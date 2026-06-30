-- disable sipago payment provider
UPDATE payment_provider
   SET sipago_client_id = NULL,
       sipago_client_secret = NULL,
       sipago_access_token = NULL,
       sipago_access_token_expiration = NULL;