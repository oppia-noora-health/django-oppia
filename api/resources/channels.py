import requests
import re
from tastypie.resources import Resource
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from tastypie.exceptions import BadRequest
from tastypie.bundle import Bundle
from django.utils.translation import gettext_lazy as _

from django.conf import settings

class DummyResponseObject:
    pk = 1  # Dummy pk to prevent Tastypie error


class ChannelResource(Resource):
    class Meta:
        resource_name = 'channel'
        object_class = dict  # Non-model resource
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

    def obj_create(self, bundle, **kwargs):
        phone_number = bundle.data.get('phone_number')

        if not phone_number:
            raise BadRequest(_("Missing 'phone_number' in request."))

        try:
            cleaned_phone_number = re.sub(r"(?!^\+)[^\d]", "", phone_number)
            base_url = self.get_api_base_url(cleaned_phone_number)
            noora_api_key = self.get_api_key(cleaned_phone_number)

            response = requests.get(
                f'{base_url}{settings.CHANNEL_URL}',
                headers={"Authorization": f"Api-Key {noora_api_key}"} 
            )
            response.raise_for_status()
            result = response.json()

            bundle.data['status'] = 'success'
            bundle.data['channels'] = result

        except requests.exceptions.RequestException as e:
            raise BadRequest(_(f"Fetching channels failed"))
        except BadRequest as br:
            raise br

        bundle.obj = DummyResponseObject()
        return bundle