import requests
import re

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
from oppia.models import Cohort

from profile.models import UserProfile, CustomField, UserProfileCustomField #update changed by namratha

from settings import constants
from settings.models import SettingProperties

from django.conf import settings


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

        missing = []
        if not phone_number:
            missing.append("phone_number")
        if not otp:
            missing.append("otp")

        if missing:
            raise BadRequest(_(f"Missing fields in request: {', '.join(missing)}."))

        try:
            cleaned_phone_number = re.sub(r"(?!^\+)[^\d]", "", phone_number)
            base_url = self.get_api_base_url(cleaned_phone_number)
            noora_api_key = self.get_api_key(cleaned_phone_number)
        except BadRequest as e:
            raise e

        # Step 1: Verify OTP
        try:
            verify_response = requests.post(
                f'{base_url}{settings.VERIFY_URL}',
                json={"code": otp, "number": cleaned_phone_number},
                headers={"Authorization": f"Api-Key {noora_api_key}"} 
            )
            verify_response.raise_for_status()
            otp_verification = verify_response.json()

            # Ensure verification actually passed
            if otp_verification.get('status') != 'success':
                raise BadRequest(_("OTP verification failed. Please try again."))

        except requests.exceptions.RequestException as e:
            raise BadRequest(_("OTP verification request failed "))
        except ValueError:
            raise BadRequest(_("Invalid JSON response from OTP verification API."))
        except KeyError:
            raise BadRequest(_("Unexpected OTP verification response structure."))

        # Step 2: OTP success → Proceed to fetch user details
        try:
            user_profile = UserProfile.objects.get(phone_number=phone_number)
            user = user_profile.user
        except UserProfile.DoesNotExist:
            raise BadRequest(_("Phone number not found. Please contact your nearest Noora Health team member for assistance."))
        except Exception as e:
            raise BadRequest(_("User lookup failed "))

        try:
            Tracker.objects.create(user=user,type='login',ip=bundle.request.META.get('REMOTE_ADDR', DEFAULT_IP_ADDRESS),agent=bundle.request.META.get('HTTP_USER_AGENT', 'unknown'))
        except Exception as e:
            raise BadRequest(_("Error logging user login tracker "))

        login(bundle.request, user)

        # assiging user to the cohort based on the custom field criteria
        for cohort in Cohort.objects.filter(criteria_based=True):
            cohort.assign_user_if_matches_criteria(user)
            
        # Custom fields
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

        # Final response
        bundle.data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'last_login': user.last_login,
            'phone_number': user_profile.phone_number,
            'organisation': user_profile.organisation,
            'job_title': user_profile.job_title,
            'custom_fields': custom_fields_data,
            'external_api_response': otp_verification,
        }

        bundle.obj = user
        key=ApiKey.objects.get(user=user)
        bundle.data['api_key']=key.key
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
