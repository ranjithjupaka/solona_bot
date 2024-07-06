import requests


url = "https://quote-api.jup.ag/v6/tokens"


payload = {}
headers = {
  'Accept': 'application/json'
}


response = requests.request("GET", url, headers=headers, data=payload)


print(response.text)


