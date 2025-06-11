
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.exceptions import BadRequest
from tastypie.models import ApiKey
from tastypie.resources import ModelResource

from api.serializers import UserJSONSerializer
from oppia import DEFAULT_IP_ADDRESS
from oppia.models import Tracker, Participant
from oppia.models import Points, Award

from profile.models import UserProfile

from settings import constants
from settings.models import SettingProperties


class UserResource(ModelResource):

    points = fields.IntegerField(readonly=True)
    badges = fields.IntegerField(readonly=True)
    scoring = fields.BooleanField(readonly=True)
    badging = fields.BooleanField(readonly=True)
    metadata = fields.CharField(readonly=True)
    course_points = fields.CharField(readonly=True)
    cohorts = fields.CharField(readonly=True)

    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        fields = ['first_name',
                  'last_name',
                  'last_login',
                  'username',
                  'points',
                  'badges',
                  'email',
                  'job_title',
                  'organisation']

        allowed_methods = ['post']
        authentication = Authentication()
        authorization = Authorization()
        serializer = UserJSONSerializer()
        always_return_data = True

    #changed by namratha
    def get_api_base_url(self, phone_number):
        if phone_number.startswith('+91'):
            return 'https://staging.noorahealth.org/hep'
        elif phone_number.startswith('+62'):
            return 'https://staging-indo.noorahealth.org/hep'
        elif phone_number.startswith('+880'):
            return 'https://staging.noorahealth.org/bd'
        elif phone_number.startswith('+977'):
            return 'https://staging.noorahealth.org/np'
        else:
            raise BadRequest(_("Unsupported country code in phone number."))
    
    #changed by namratha
    @staticmethod
    def normalize_number(number):
        match = re.match(r'^(\+\d{2})(\d{10})$', number.replace(" ", ""))
        if not match:
            raise BadRequest(_("Invalid phone number format."))
        return f"{match.group(1)} {match.group(2)}"

    # def obj_create(self, bundle, **kwargs):

    #     if 'username' not in bundle.data:
    #         raise BadRequest(_(u'Username missing'))

    #     if 'password' not in bundle.data:
    #         raise BadRequest(_(u'Password missing'))

    #     username = bundle.data['username']
    #     password = bundle.data['password']

    #     u = authenticate(username=username, password=password)
    #     if u is not None and u.is_active:
    #         login(bundle.request, u)
    #         # Add to tracker
    #         tracker = Tracker()
    #         tracker.user = u
    #         tracker.type = 'login'
    #         tracker.ip = bundle.request.META.get('REMOTE_ADDR', DEFAULT_IP_ADDRESS)
    #         tracker.agent = bundle.request.META.get('HTTP_USER_AGENT', 'unknown')
    #         tracker.save()
    #     else:
    #         raise BadRequest(_(u'Authentication failure'))

    #     del bundle.data['password']
    #     key = ApiKey.objects.get(user=u)
    #     bundle.data['api_key'] = key.key

    #     try:
    #         profile = UserProfile.objects.get(user__id=bundle.obj.id)
    #         bundle.data['job_title'] = profile.job_title
    #         bundle.data['organisation'] = profile.organisation

    #         customfields = profile.get_customfields_dict()
    #         bundle.data.update(customfields)

    #     except UserProfile.DoesNotExist:
    #         bundle.data['job_title'] = ''
    #         bundle.data['organisation'] = ''

    #     bundle.obj = u
    #     return bundle

    #changed by namratha
    def obj_create(self, bundle, **kwargs):
        #changed by namratha
        phone_number = bundle.data.get('phone_number')
        otp = bundle.data.get('code')

        if not phone_number or not otp:
            raise BadRequest(_("Both phone number and OTP are required."))

        try:
            normalized_phone_number = self.normalize_number(phone_number)
        except BadRequest as e:
            raise e

        # EARLY EXIT if user does not exist
        try:
            user_profile = UserProfile.objects.get(phone_number=normalized_phone_number)
            user = user_profile.user
        except UserProfile.DoesNotExist:
            raise BadRequest(_("User does not exist. Please register before logging in."))

        try:
            base_url = self.get_api_base_url(phone_number)
        except BadRequest as e:
            raise e

        # Verify OTP
        try:
            verify_response = requests.post(
                f'{base_url}/api/v1/academy-auth/verify/',
                json={"code": otp, "number": phone_number},
                headers={"Authorization": "Api-Key jMpk2uHS.5XZLCAjWbvfRXCBKLsICZjFGAAnsKRT8"}
            )
            verify_response.raise_for_status()
            otp_verification = verify_response.json()
        except requests.exceptions.RequestException as e:
            raise BadRequest(_("OTP verification request failed: ") + str(e))
        except ValueError:
            raise BadRequest(_("Invalid JSON response from OTP verification API."))

        # Get profile
        try:
            profile_response = requests.get(
                f"{base_url}/api/v1/academy-auth/profile/{phone_number}",
                headers={"Authorization": "Api-Key jMpk2uHS.5XZLCAjWbvfRXCBKLsICZjFGAAnsKRT8"}
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()
        except requests.exceptions.RequestException:
            raise BadRequest(_("Phone number not found. Please contact your nearest Noora Health team member for assistance."))

        if not profile_data or 'error' in profile_data or 'detail' in profile_data:
            raise BadRequest(_("User profile not found or invalid response received from profile API."))

        # Update user.username if changed
        if user.username != phone_number:
            user.username = phone_number

        updated = False
        if user_profile.organisation != profile_data.get('organisation', ''):
            user_profile.organisation = profile_data.get('organisation', '')
            updated = True
        if user_profile.job_title != profile_data.get('job_title', ''):
            user_profile.job_title = profile_data.get('job_title', '')
            updated = True
        if updated:
            user_profile.save()

        try:
            custom_fields = CustomField.objects.all()
            for custom_field in custom_fields:
                value = profile_data.get(str(custom_field.id))
                if value is None:
                    continue

                field_obj, created = UserProfileCustomField.objects.get_or_create(
                    user=user,
                    key_name=custom_field
                )

                if custom_field.type == 'int':
                    field_obj.value_int = int(value)
                    field_obj.value_bool = None
                    field_obj.value_str = None
                elif custom_field.type == 'bool':
                    val_bool = value if isinstance(value, bool) else str(value).lower() in ['true', '1', 'yes']
                    field_obj.value_bool = val_bool
                    field_obj.value_int = None
                    field_obj.value_str = None
                else:
                    field_obj.value_str = str(value)
                    field_obj.value_int = None
                    field_obj.value_bool = None

                field_obj.save()

        except Exception as e:
            raise BadRequest(_("Saving custom fields failed: ") + str(e))

        try:
            ApiKey.objects.get_or_create(user=user)
            login(bundle.request, user)
        except Exception as e:
            raise BadRequest(_("Login or API key generation failed: ") + str(e))

        try:
            Tracker.objects.create(
                user=user,
                type='login',
                ip=bundle.request.META.get('REMOTE_ADDR', DEFAULT_IP_ADDRESS),
                agent=bundle.request.META.get('HTTP_USER_AGENT', 'unknown')
            )
        except Exception as e:
            raise BadRequest(_("Error logging user login tracker: ") + str(e))

        custom_fields_data = {}
        user_custom_fields = UserProfileCustomField.objects.filter(user=user)
        for field in user_custom_fields:
            if field.key_name.type == 'int':
                value = field.value_int
            elif field.key_name.type == 'bool':
                value = field.value_bool
            else:
                value = field.value_str

            custom_fields_data[field.key_name.label] = value

        bundle.data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'last_login': user.last_login,
            'phone_number': user_profile.phone_number if user_profile else '',
            'organisation': user_profile.organisation if user_profile else '',
            'job_title': user_profile.job_title if user_profile else '',
            'custom_fields': custom_fields_data,
            'external_api_response': profile_data,
        }

        bundle.obj = user
        return bundle

    def dehydrate_cohorts(self, bundle):
        return Participant.get_user_cohorts(bundle.request.user)

    def dehydrate_points(self, bundle):
        points = Points.get_userscore(
            User.objects.get(username=bundle.request.user.username))
        return points

    def dehydrate_badges(self, bundle):
        badges = Award.get_userawards(
            User.objects.get(username=bundle.request.user.username))
        return badges

    def dehydrate_scoring(self, bundle):
        return SettingProperties.get_bool(
            constants.OPPIA_POINTS_ENABLED,
            settings.OPPIA_POINTS_ENABLED)

    def dehydrate_badging(self, bundle):
        return SettingProperties.get_bool(
            constants.OPPIA_BADGES_ENABLED,
            settings.OPPIA_BADGES_ENABLED)

    def dehydrate_metadata(self, bundle):
        return settings.OPPIA_METADATA

    def dehydrate_course_points(self, bundle):
        course_points = list(
            Points.objects
            .exclude(course=None)
            .filter(user=bundle.request.user)
            .values('course__shortname')
            .annotate(total_points=Sum('points')))
        return course_points
    
    #changed by namratha
    def dehydrate_api_key(self, bundle):
        try:
            key = ApiKey.objects.get(user=bundle.obj)
            return key.key
        except ApiKey.DoesNotExist:
            return None
