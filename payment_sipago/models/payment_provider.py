import logging
import pprint
from datetime import datetime

import requests
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.addons.payment_sipago.const import AUTH_SERVER_URL, CHECKOUT_URL, SUPPORTED_CURRENCIES
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('sipago', 'Sipago')], ondelete={'sipago': 'set default'})

    sipago_env = fields.Selection(
        selection=[
            ('DEVELOPMENT', 'Development'),
            ('PRODUCTION', 'Production'),
        ],
        string='Sipago Environment',
        groups='base.group_system',
        required_if_provider='sipago',
        default='DEVELOPMENT',
        help='Development is used for testing purposes, while Production is used for live transactions.'
        ' For development credentials, look at https://docs.sipago.coop/API%20Cobros/credencialDev',
    )

    sipago_client_id = fields.Char(
        string='Sipago Client ID',
        required_if_provider='sipago',
        groups='base.group_system',
    )

    sipago_client_secret = fields.Char(
        string='Sipago Client Secret',
        required_if_provider='sipago',
        groups='base.group_system',
    )

    sipago_access_token = fields.Char(
        string='Sipago Access Token',
        groups='base.group_system',
    )

    sipago_access_token_expiration = fields.Datetime(
        string='Sipago Token Expiration',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Override of `payment` to unlist Sipago providers for unsupported currencies."""
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            providers = providers.filtered(lambda p: p.code != 'sipago')

        return providers

    def sipago_set_JWT_token(self):
        """Get the JWT token from Sipago API.

        :return: The JWT token.
        :rtype: str
        :raise ValidationError: If an HTTP error occurs.
        """
        url = f'{AUTH_SERVER_URL[self.sipago_env]}/oauth/token'
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.sipago_client_id,
            'client_secret': self.sipago_client_secret,
            'scope': '*',
        }
        headers = {'Content-Type': 'application/json'}

        try:
            _logger.info('Requesting JWT token from Sipago API')
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            _logger.exception('Failed to retrieve JWT token from Sipago API')
            raise ValidationError(_('Sipago: Failed to retrieve JWT token. Please check your credentials.'))

        try:
            token_data = response.json()
            self.sipago_access_token = token_data.get('access_token')
            self.sipago_access_token_expiration = datetime.utcfromtimestamp(token_data.get('expires_in'))

        except (ValueError, TypeError):
            raise ValidationError(_('Sipago: Invalid response format while retrieving JWT token.'))

    def token_is_expired(self):
        """Check if the Sipago JWT token is expired.
        :return: True if the token is expired or has no expiration date, False otherwise.
        :rtype: bool
        """
        if not self.sipago_access_token_expiration:
            return True
        return fields.Datetime.to_datetime(self.sipago_access_token_expiration) < fields.Datetime.now()

    def ensure_valid_token(self):
        """Ensure the Sipago JWT token is valid and refresh it if necessary."""
        if not self.sipago_access_token or self.token_is_expired():
            _logger.info('There is no Sipago token or it is expired, refreshing it...')
            self.sipago_set_JWT_token()

    def _sipago_make_request(self, endpoint, payload=None, method='POST'):
        """Make a request to Sipago API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        self.ensure_valid_token()

        url = urls.url_join(CHECKOUT_URL[self.sipago_env], endpoint)

        def _send_request():
            headers = {
                'Authorization': f'Bearer {self.sipago_access_token}',
                'Content-Type': 'application/vnd.api+json',
            }
            if method == 'GET':
                return requests.get(url, params=payload, headers=headers, timeout=10)
            return requests.post(url, json=payload, headers=headers, timeout=10)

        try:
            response = _send_request()
            if response.status_code == 401:
                _logger.warning(
                    'Sipago API returned 401 at %s, refreshing the JWT token and retrying once.',
                    url,
                )
                self.sipago_set_JWT_token()
                response = _send_request()
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    'Invalid API request at %s with data:\n%s',
                    url,
                    pprint.pformat(payload),
                )
                try:
                    response_content = response.json()
                    raise ValidationError(
                        'Sipago: '
                        + _(
                            "The communication with the API failed. Sipago gave us the following response:\n '%s'",
                            pprint.pformat(response_content),
                        )
                    )
                except ValueError:  # The response can be empty when the access token is wrong.
                    raise ValidationError(
                        'Sipago: '
                        + _(
                            'The communication with the API failed. The response is empty. Please'
                            ' verify your access token.'
                        )
                    )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception('Unable to reach endpoint at %s', url)
            raise ValidationError('Sipago: ' + _('Could not establish the connection to the API.'))
        return response.json()
