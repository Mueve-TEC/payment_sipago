import requests
import pprint
from urllib.parse import urljoin
import datetime


class SipagoTest:
    sipago_access_token = None
    sipago_client_secret = None
    sipago_client_id = None
    sipago_access_token_expiration = None

    def sipago_set_JWT_token(self):
        """ Get the JWT token from Sipago API.

        :return: The JWT token.
        :rtype: str
        :raise ValidationError: If an HTTP error occurs.
        """
        url = f'https://auth.preprod.geopagos.com/oauth/token'
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.sipago_client_id,
            "client_secret": self.sipago_client_secret,
            "scope": "*"
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print("Failed to retrieve JWT token from Sipago API")
            raise Exception(
                ("Sipago: Failed to retrieve JWT token. Please check your credentials."))

        try:
            token_data = response.json()
            self.sipago_access_token = token_data.get('access_token')
            # TODO: debug
            self.sipago_access_token_expiration = datetime.datetime.now() + \
                datetime.timedelta(seconds=token_data.get('expires_in'))

        except ValueError:
            raise Exception(
                ("Sipago: Invalid response format while retrieving JWT token."))

    def ensure_valid_token(self):
        if self.sipago_access_token is None or \
                self.sipago_access_token_expiration is None or \
                datetime.datetime.now() > self.sipago_access_token_expiration:
            self.sipago_set_JWT_token()

    def sipago_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Sipago API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_valid_token()

        url = urljoin("https://api-cabal.preprod.geopagos.com", endpoint)
        headers = {
            'Authorization': f'Bearer {self.sipago_access_token}',
            'Content-Type': 'application/vnd.api+json'
        }
        try:
            if method == 'GET':
                response = requests.get(
                    url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=10)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    print(
                        "Invalid API request at %s with data:\n%s", url, pprint.pformat(
                            payload),
                    )
                    try:
                        response_content = response.json()
                        error_code = response_content.get('error')
                        error_message = response_content.get('message')
                        raise Exception("Sipago: " + (
                            "The communication with the API failed. Sipago gave us the"
                            " following information: '%s' (code %s)", error_message, error_code
                        ))
                    except ValueError:  # The response can be empty when the access token is wrong.
                        raise Exception("Sipago: " + (
                            "The communication with the API failed. The response is empty. Please"
                            " verify your access token."
                        ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise Exception(
                "Sipago: " +
                ("Could not establish the connection to the API.")
            )
        return response.json()


def main():
    sipago_test = SipagoTest()
    sipago_test.sipago_client_id = input("Enter your client ID: ")
    sipago_test.sipago_client_secret = input("Enter your client secret: ")

    # Example of making a request

    endpoint = "/api/v2/orders"
    payload = {
        "data": {
            "attributes": {
                "redirect_urls": {
                    "success": "https://dominio.com/?ref=ok",
                    "failed": "https://dominio.com/?ref=fallo"
                },
                "currency": "032",
                "shipping": {
                    "name": "Precio fijo",
                    "price": {
                        "currency": "032",
                        "amount": 2000
                    }
                },
                "items": [{
                    "id": 31,
                    "name": "Silla Eames Base Madera",
                    "unitPrice": {
                        "currency": "032",
                        "amount": 1000
                    },
                    "quantity": 1
                }]
            }
        }
    }
    print("Making a request to the API...")
    response = sipago_test.sipago_make_request(endpoint, payload)

    print("\nAccess Token:", sipago_test.sipago_access_token)
    print("\nToken Expiration:", sipago_test.sipago_access_token_expiration)

    print("\nResponse checkout link:",
          response["data"]["attributes"]["links"]["checkout"])


if __name__ == "__main__":
    main()
