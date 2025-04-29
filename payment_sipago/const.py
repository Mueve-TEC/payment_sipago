
from odoo import _


# TODO: Currency codes of the currencies supported by Sipago in ISO 4217 format.
SUPPORTED_CURRENCIES = [
]

# TODO: Mapping of transaction states to Sipago payment statuses.
TRANSACTION_STATUS_MAPPING = {
    "PENDING": "PENDING",
    "EXPIRED": "EXPIRED",
    "FAILED_CHECKOUT": "ERROR",
    "FAILED": "FAILED",
    "SUCCESS": "SUCCESS",
}

# TODO: Mapping of error states to Sipago error messages.
ERROR_MESSAGE_MAPPING = {
}

AUTH_SERVER_URL = {
    "DEVELOPMENT": "https://auth.preprod.geopagos.com",
    "PRODUCTION": "https://auth.geopagos.com",
}

CHECKOUT_URL = {
    "DEVELOPMENT": "https://api-cabal.preprod.geopagos.com",
    "PRODUCTION": "https://api.sipago.coop"
}
