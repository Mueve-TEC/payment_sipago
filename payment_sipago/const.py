from odoo import _

# Currency codes supported by Sipago (ARS - Argentine Peso, code 032)
SUPPORTED_CURRENCIES = [
    'ARS',  # Argentine Peso - ISO code 032
]

# Mapping of ISO 4217 currency names to Sipago numeric currency codes
CURRENCY_CODES = {
    'ARS': '032',  # Argentine Peso
}

# Mapping of transaction states to Sipago statuses (both order and payment statuses)
# Format: internal_status -> [list_of_external_statuses]
ORDER_STATUS_MAPPING = {
    'pending': ['PENDING'],
    'done': ['SUCCESS'],
    'canceled': ['EXPIRED'],
    'error': ['FAILED', 'FAILED_CHECKOUT'],
}

# Error messages for Sipago states based on official documentation
ERROR_MESSAGE_MAPPING = {
    'FAILED_CHECKOUT': _('There was an error in the checkout process after user payment'),
    'FAILED': _('Order creation failed before user payment'),
    'default': _('Payment was rejected for unknown reasons'),
}

AUTH_SERVER_URL = {
    'DEVELOPMENT': 'https://auth.stg.geopagos.io',
    'PRODUCTION': 'https://auth.prd.geopagos.io',
}

CHECKOUT_URL = {'DEVELOPMENT': 'https://api-cabal.preprod.geopagos.com', 'PRODUCTION': 'https://api.sipago.coop'}
