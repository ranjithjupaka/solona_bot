import json

import requests
from solathon.core.instructions import transfer
from solathon import Client, Transaction, PublicKey, Keypair

url = "https://api.mainnet-beta.solana.com"
client = Client(url)


def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair()
    public_key = keypair.public_key
    secret_key = keypair.private_key
    print(public_key, secret_key)

    return "3RQ1yB5MZMf5WCed9TyDEbpZLA9ZHMBqNPqKP5QTxSQJ", "4ebYS83MWMV3FjQNfdNCYKAyPuujyQnTuhGX8j4v8E5hPhDEau3aqRvRiL9oMStoi29CfjpXsUp32HpARQpvZUve"
    # return "8v7Dk3F9LGxcYDUxwAAiSjxqB6zP1J1fegLcSThCkEGC", "5t8RF51xjnjBv1zxtEK6T6tzFd4zBdYqed9qHCHhmUPWEKXDwuwX5bxNnmFiNfLgUHxX6s4o7b7iwSr6SzE2gMpp"


def get_wallet_balance(public_key_str):
    public_key = PublicKey(public_key_str)
    balance = client.get_balance(public_key)
    print(balance)
    balance_sol = balance / 1000000000

    return balance_sol


def get_token_balance(public_key_str):
    token_balances = []

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

            if int(val['account']['data']['parsed']['info']['tokenAmount']['amount']) > 0:
                token_balances.append({'token_address': val['account']['data']['parsed']['info']['mint'],
                                       'uiAmount': val['account']['data']['parsed']['info']['tokenAmount']['uiAmount'],
                                       'amount': val['account']['data']['parsed']['info']['tokenAmount']['amount']
                                       })

        return token_balances

    except Exception as e:
        print(e)
        return None


def send_sol(from_secret_key, to_public_key, amount_sol):
    try:
        print('args---',from_secret_key,to_public_key,amount_sol)
        sender = Keypair.from_private_key(from_secret_key)
        receiver = PublicKey(to_public_key)
        amount = int(amount_sol * 1000000000)
        fees = client.get_fees()
        gas_fees = fees['value']['feeCalculator']['lamportsPerSignature']
        print(gas_fees)
        trans_amount = amount-gas_fees
        print('trans_amount',trans_amount)

        instruction = transfer(
            from_public_key=sender.public_key,
            to_public_key=receiver,
            lamports=trans_amount
        )

        transaction = Transaction(instructions=[instruction], signers=[sender])

        result = client.send_transaction(transaction)
        print("Transaction response: ", result)
        return result
    except Exception as e:
        print(e)
        return None

# sender = Keypair.from_private_key("4ebYS83MWMV3FjQNfdNCYKAyPuujyQnTuhGX8j4v8E5hPhDEau3aqRvRiL9oMStoi29CfjpXsUp32HpARQpvZUve")
# print(sender.public_key,sender.private_key)
# fees = client.get_fees()
# print(fees['value']['feeCalculator']['lamportsPerSignature'])
# create_wallet()
# token_bal = get_token_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")
# print(token_bal)
# wallet_bal = get_wallet_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")
# print(wallet_bal)

# send_sol("4ebYS83MWMV3FjQNfdNCYKAyPuujyQnTuhGX8j4v8E5hPhDEau3aqRvRiL9oMStoi29CfjpXsUp32HpARQpvZUve",
#          "HFC9JZVhr5QPBJ6fwFZcuJ4zKuwam9rjgQXaTBP5rj5x", 0.004)
