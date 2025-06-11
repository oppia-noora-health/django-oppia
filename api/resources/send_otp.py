import requests
from tastypie.resources import Resource
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from tastypie.exceptions import BadRequest
from tastypie.bundle import Bundle
from django.utils.translation import gettext_lazy as _


class DummyResponseObject:
    pk = 1  # Dummy pk to prevent Tastypie error


class SendOTPResource(Resource):
    class Meta:
        resource_name = 'sendotp'
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
        channel = bundle.data.get('channel')
        print(phone_number,channel)

        if not phone_number:
            raise BadRequest(_("Missing 'phonenumber' in request."))

        try:
            base_url = self.get_api_base_url(phone_number)

            response = requests.post(
                f'{base_url}/api/v1/academy-auth/start/',
                json={"number": phone_number, "channel": channel},
                headers={"Authorization": "Api-Key jMpk2uHS.5XZLCAjWbvfRXCBKLsICZjFGAAnsKRT8"}
            )
            response.raise_for_status()
            result = response.json()

            bundle.data['status'] = 'success'
            bundle.data['response'] = 'we texted you a login code'

        except requests.exceptions.RequestException as e:
            raise BadRequest(_(f"OTP sending failed: {str(e)}"))
        except BadRequest as br:
            raise br

        bundle.obj = DummyResponseObject()  # Prevent .pk error
        return bundle