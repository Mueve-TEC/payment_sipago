# Load environment variables from .env file
include .env
export

.PHONY: auth checkout

auth:
	curl --location --request POST "$(AUTH_URL)/oauth/token" --header "Content-Type: application/json" --data-raw "{ \
	\"grant_type\": \"client_credentials\", \
	\"client_id\": \"$(CLIENT_ID)\", \
	\"client_secret\": \"$(CLIENT_SECRET)\", \
	\"scope\": \"*\" \
	}"

