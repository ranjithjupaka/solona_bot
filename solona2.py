import json

import requests
from solathon.core.instructions import transfer
from solathon import Client, Transaction, PublicKey, Keypair

url = "https://api.mainnet-beta.solana.com"
client = Client(url)

token_balances = []


def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair()
    public_key = keypair.public_key
    secret_key = keypair.public_key
    print(public_key, secret_key)

    # return public_key, secret_key
    return "4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD", "5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"


def get_wallet_balance(public_key_str):
    public_key = PublicKey(public_key_str)
    balance = client.get_balance(public_key)
    print(balance)
    balance_sol = balance / 1000000000

    return balance_sol


def get_token_balance(public_key_str):
    headers = {"Content-Type": "application/json"}

    try:
        # Get token accounts
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                public_key_str,
                {
                    "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                },
                {
                    "encoding": "jsonParsed"
                }
            ]
        }

        result = requests.post(url, headers=headers, data=json.dumps(payload))
        # print(result.json())

        value = result.json()["result"]["value"]
        print(value)

        for val in value:
            print(val['account']['data']['parsed']['info'])
            print(val['account']['data']['parsed']['info']['mint'],
                  val['account']['data']['parsed']['info']['tokenAmount']['uiAmount'])

            token_balances.append({'token_address': val['account']['data']['parsed']['info']['mint'],
                                   'Amount': val['account']['data']['parsed']['info']['tokenAmount']['uiAmount']})

        return token_balances

    except Exception as e:
        print(e)
        return None


def send_sol(from_secret_key, to_public_key, amount_sol):
    sender = Keypair.from_private_key(from_secret_key)
    receiver = PublicKey(to_public_key)
    amount = int(amount_sol * 1000000000)

    instruction = transfer(
        from_public_key=sender.public_key,
        to_public_key=receiver,
        lamports=amount
    )

    transaction = Transaction(instructions=[instruction], signers=[sender])

    result = client.send_transaction(transaction)
    print("Transaction response: ", result)


create_wallet()
token_bal = get_token_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")
print(token_balances)
wallet_bal = get_wallet_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")
print(wallet_bal)

# send_sol("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq",
#          "HFC9JZVhr5QPBJ6fwFZcuJ4zKuwam9rjgQXaTBP5rj5x", 0.004)
