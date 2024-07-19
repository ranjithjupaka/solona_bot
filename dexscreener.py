import requests

token_details = {}


def get_token_details(token_address):
    try:
        response = requests.get(f"https://api.dexscreener.io/latest/dex/tokens/{token_address}")
        response.raise_for_status()
        resp = response.json()

        if resp['pairs']:
            print('token info', resp['pairs'][0])
            token_details['name'] = resp['pairs'][0]['baseToken']['name']
            token_details['symbol'] = resp['pairs'][0]['baseToken']['symbol']
            token_details['address'] = resp['pairs'][0]['baseToken']['address']
            token_details['marketCap'] = resp['pairs'][0]["fdv"]
            token_details['price'] = resp['pairs'][0]['priceUsd']
            token_details['priceChange'] = resp['pairs'][0]['priceChange']
            # print(token_details)

        return token_details

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return token_details

# token = get_token_details("HXpEPzcPBqzvzgLifMxM4KbTpzBHSCfFe9BBdULNpump")
# print(token)
