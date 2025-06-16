import requests
import re
from tastypie.resources import Resource
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from tastypie.exceptions import BadRequest
from tastypie.bundle import Bundle
from django.utils.translation import gettext_lazy as _


class DummyResponseObject:
    pk = 2 # Dummy pk to prevent Tastypie error


class ProfileExternalResource(Resource):
    class Meta:
        resource_name = 'profileexternal'
        object_class = dict  # Non-model resource
        allowed_methods = ['post']
        authentication = Authentication()
        authorization = Authorization()
        always_return_data = True

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

    def obj_create(self, bundle, **kwargs):
        phone_number = bundle.data.get('phone_number')

        if not phone_number:
            raise BadRequest(_("Missing 'phone_number' in request."))

        try:
            cleaned_phone_number = re.sub(r"\s+", "", phone_number)
            base_url = self.get_api_base_url(cleaned_phone_number)

            response = requests.get(
                f'{base_url}/api/v1/academy-auth/profile/{cleaned_phone_number}',
                headers={"Authorization": "Api-Key jMpk2uHS.5XZLCAjWbvfRXCBKLsICZjFGAAnsKRT8"}
            )
            response.raise_for_status()
            result = response.json()

            if not result or 'error' in result or 'detail' in result:
                raise BadRequest(_("Phone number not found. Please contact your nearest Noora Health team member for assistance."))

            bundle.data['status'] = 'success'
            bundle.data['profile'] = result
            print(bundle)

        except requests.exceptions.RequestException as e:
            raise BadRequest(_("Fetching profile failed: ") + str(e))
        except BadRequest as br:
            raise br

        bundle.obj = DummyResponseObject()
        return bundle
