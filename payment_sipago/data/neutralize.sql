-- disable sipago payment provider
UPDATE payment_provider
SET sipago_access_token = NULL;