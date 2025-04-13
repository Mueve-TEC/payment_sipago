include .env
export

.PHONY: auth checkout

auth:
	curl --silent --location --request POST "$(AUTH_URL)/oauth/token" \
		--header "Content-Type: application/json" \
		--data-raw "{ \
		\"grant_type\": \"client_credentials\", \
		\"client_id\": \"$(CLIENT_ID)\", \
		\"client_secret\": \"$(CLIENT_SECRET)\", \
		\"scope\": \"*\" \
		}" | jq -r '.access_token' > token.txt
	@echo "Token guardado en token.txt"


checkout:
	@if [ ! -f token.txt ]; then \
		echo "Error: no se encontró el archvio token.txt, ejecute primero el comando 'make auth'"; \ 
		exit 1; \
	fi

	curl --location --request POST "$(CHECKOUT_URL)/api/v2/orders" --header "Authorization: Bearer $(shell cat token.txt)" --header "Content-Type: application/vnd.api+json" --data-raw "{ \
		\"data\": { \
			\"attributes\": { \
				\"redirect_urls\": { \
				\"success\": \"https://dominio.com/?ref=ok\", \
				\"failed\": \"https://dominio.com/?ref=fallo\" \
				}, \
				\"currency\": \"032\", \
				\"shipping\": { \
				\"name\": \"Precio fijo\", \
				\"price\": { \
					\"currency\": \"032\", \
					\"amount\": 2000 \
				} \
				}, \
				\"items\": [{ \
				\"id\": 31, \
				\"name\": \"Silla Eames Base Madera\", \
				\"unitPrice\": { \
					\"currency\": \"032\", \
					\"amount\": 1000 \
				}, \
				\"quantity\": 1 \
				}] \
			} \
		} \
	}" | jq -r '.data.attributes.links.checkout' || echo "Error: No se pudo obtener el enlace de checkout"