import re
import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as gettext
from tastypie.resources import Resource
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from tastypie.exceptions import BadRequest
from tastypie.models import ApiKey

from oppia import DEFAULT_IP_ADDRESS
from oppia.models import Tracker
from profile.models import UserProfile, CustomField, UserProfileCustomField
from settings import constants
from settings.models import SettingProperties
from api.resources.base_register import RegisterBaseResource
from profile.utils import set_exclude_from_reporting

class ExternalProfileResource(RegisterBaseResource):
    class Meta:
        resource_name = 'externalprofile'
        object_class = User
        allowed_methods = ['post']
        authentication = Authentication()
        authorization = Authorization()
        always_return_data = True

    def get_api_base_url(self, phone_number):
        if phone_number.startswith('+91'):
            return settings.PROD_INDIA_URL
        elif phone_number.startswith('+62'):
            return settings.PROD_INDONESIA_URL
        elif phone_number.startswith('+977'):
            return settings.PROD_NEPAL_URL
        elif phone_number.startswith('+880'):
            return settings.PROD_BANGLADESH_URL
        else:
            raise BadRequest(_("Unsupported country code in phone number."))
    
    def get_api_key(self, phone_number):
        if phone_number.startswith('+91'):
            return settings.NOORA_API_KEY_INDIA
        elif phone_number.startswith('+62'):
            return settings.NOORA_API_KEY_INDONESIA
        elif phone_number.startswith('+977'):
            return settings.NOORA_API_KEY_NEPAL
        elif phone_number.startswith('+880'):
            return settings.NOORA_API_KEY_BANGLADESH
        else:
            raise BadRequest(_("Unsupported country code in phone number."))

    def insert_country_language_custom_fields(self, user, country, language):
        for field_name, value in [('country', country), ('language', language)]:
            if value:
                try:
                    custom_field = CustomField.objects.get(id=field_name)
                    cf_obj, _ = UserProfileCustomField.objects.get_or_create(
                        key_name=custom_field,
                        user=user
                    )
                    if custom_field.type == 'str' and (cf_obj.value_str or '') != value:
                        cf_obj.value_str = value
                        cf_obj.save()
                    elif custom_field.type == 'int' and cf_obj.value_int != int(value):
                        cf_obj.value_int = int(value)
                        cf_obj.save()
                    elif custom_field.type == 'bool' and cf_obj.value_bool != bool(value):
                        cf_obj.value_bool = bool(value)
                        cf_obj.save()
                except CustomField.DoesNotExist:
                    continue 

    def update_or_create_custom_field(self, user, external_profile):
        custom_fields = CustomField.objects.all()
        for custom_field in custom_fields:
            field_id = custom_field.id
            if field_id in external_profile:
                value = external_profile[field_id]
                cf_obj, _ = UserProfileCustomField.objects.get_or_create(
                    key_name=custom_field,
                    user=user
                )
                updated = False
                if custom_field.type == 'int' and cf_obj.value_int != value:
                    cf_obj.value_int = value
                    updated = True
                elif custom_field.type == 'bool' and cf_obj.value_bool != value:
                    cf_obj.value_bool = value
                    updated = True
                elif custom_field.type == 'str' and (cf_obj.value_str or '') != value:
                    cf_obj.value_str = value
                    updated = True
                if updated:
                    cf_obj.save()
    
    def obj_create(self, bundle, **kwargs):
        phone_number = bundle.data.get('phone_number')
        country = bundle.data.get('country')
        language = bundle.data.get('language')

        missing = []
        if not phone_number:
            missing.append("phone_number")
        if not country:
            missing.append("country")
        if not language:
            missing.append("language")

        if missing:
            raise BadRequest(gettext(f"Missing fields in request: {', '.join(missing)}."))

        cleaned_phone_number = re.sub(r"(?!^\+)[^\d]", "", phone_number)

        user_profile = UserProfile.objects.filter(phone_number=phone_number).first()

        # Always fetch external profile
        try:
            base_url = self.get_api_base_url(cleaned_phone_number)
            noora_api_key = self.get_api_key(cleaned_phone_number)
            response = requests.get(
                f'{base_url}{settings.PROFILE_URL}{cleaned_phone_number}/',
                headers={"Authorization": f"Api-Key {noora_api_key}"}
            )
            response.raise_for_status()
            external_profile = response.json()

            if not external_profile or not external_profile.get('phone_number'):
                raise BadRequest(gettext("Phone number not found. Please contact your nearest Noora Health team member for Assistance."))
        except requests.exceptions.RequestException as e:
            raise BadRequest(gettext("Phone number not found. Please contact your nearest Noora Health team member for Assistance") )

        if user_profile:
            user = user_profile.user
            # set_exclude_from_reporting(user) added it in staging server for testing purpose
            # Compare and update User fields
            updated = False
            first_name = external_profile.get('first_name', '').strip()
            last_name = external_profile.get('last_name', '')
            email = external_profile.get('email', '')

            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if email and user.email != email:
                user.email = email
                updated = True
            if updated:
                user.save()

            # Update existing custom fields
            self.update_or_create_custom_field(user, external_profile)
            self.insert_country_language_custom_fields(user, country, language)

        else:
            # Create new user
            external_name = external_profile.get('name', '').strip()
            external_phone = external_profile.get('phone_number', cleaned_phone_number)
            username = f"{external_phone}_{slugify(external_name)}" if external_name else external_phone

            if User.objects.filter(username=username).exists():
                raise BadRequest(gettext(f'Username "{username}" already exists.'))

            try:
                user = User.objects.create_user(username=username)
                user.first_name = external_name
                user.last_name = external_profile.get('last_name', '')
                user.email = external_profile.get('email', '')
                user.set_unusable_password()
                user.save()
            except IntegrityError:
                raise BadRequest(gettext("Could not create user. Username conflict."))

            # Fill bundle
            bundle.obj = user
            bundle.data['phoneno'] = phone_number
            bundle.data['first_name'] = user.first_name
            bundle.data['last_name'] = user.last_name
            bundle.data['email'] = user.email
            bundle.data['username'] = username

            # Add custom fields dynamically
            valid_custom_fields = CustomField.objects.values_list('id', flat=True)
            for field in valid_custom_fields:
                if field in external_profile:
                    bundle.data[field] = external_profile[field]

            # Create profile and custom fields
            self.process_register_base_profile(bundle)
            self.process_register_custom_fields(bundle)
            self.insert_country_language_custom_fields(user, country, language)
            # set_exclude_from_reporting(user) added it in staging server for testing purpose

            # Track registration
            Tracker.objects.create(
                user=user,
                type='register',
                ip=bundle.request.META.get('REMOTE_ADDR', DEFAULT_IP_ADDRESS),
                agent=bundle.request.META.get('HTTP_USER_AGENT', 'unknown')
            )

        # Finalize login and response
        login(bundle.request, user)
        api_key, _ = ApiKey.objects.get_or_create(user=user)

        bundle.data['status'] = 'success'
        bundle.data['username'] = user.username
        bundle.data['api_key'] = api_key.key
        bundle.data['profile'] = external_profile
        bundle.obj = user

        return bundle
