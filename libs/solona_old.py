import asyncio
import json
import os
import time

import requests
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.transaction import Transaction, TransactionInstruction
from solana.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts, TokenAccountOpts
from solana.blockhash import Blockhash
from base58 import b58decode
from solana.rpc.commitment import Confirmed


import os
import sys
import site




token_balances = []


def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair.generate()
    public_key = keypair.public_key
    secret_key = keypair.secret_key
    secret_key = secret_key.hex()
    print(public_key, secret_key)

    # return public_key, secret_key
    return "4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD", "5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"


def get_wallet_balance(public_key_str):
    client = Client("https://api.mainnet-beta.solana.com")
    public_key = PublicKey(public_key_str)
    balance = client.get_balance(public_key)
    balance_sol = balance.value / 1000000000

    return balance_sol


def get_token_balance(public_key_str):
    url = "https://api.mainnet-beta.solana.com"
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


def get_gas_price():
    # Initialize Solana RPC client
    client = Client("https://api.mainnet-beta.solana.com")

    # Fetch the fee calculator for the latest block
    response = client.get_fees()
    fee_calculator = response['result']['value']['feeCalculator']
    lamports_per_signature = fee_calculator['lamportsPerSignature']

    # Convert lamports to SOL
    gas_price_sol = lamports_per_signature / 1e9  # 1 SOL = 1,000,000,000 lamports

    return gas_price_sol


def get_latest_blockhash(client):
    return client.get_recent_blockhash()['result']['value']['blockhash']


def send_sol(from_secret_key, to_public_key_str, amount_sol):
    print(from_secret_key,to_public_key_str,amount_sol)
    client = Client("https://api.mainnet-beta.solana.com")
    secret_key_bytes = b58decode(from_secret_key)
    from_keypair = Keypair.from_secret_key(secret_key_bytes)
    print(from_keypair)
    amount_lamports = int(amount_sol * 1000000000)
    gas_fees = int(0.000005*1000000000)
    trans_amount = amount_lamports-gas_fees
    print(trans_amount)

    recent_blockhash = client.get_latest_blockhash().value.blockhash
    print('recent hash', recent_blockhash)

    # Create the transaction
    transaction = Transaction()
    transaction.add(transfer(TransferParams(
        from_pubkey=from_keypair.public_key,
        to_pubkey=PublicKey(to_public_key_str),
        lamports=trans_amount
    )))

    # Set the blockhash
    transaction.recent_blockhash = str(recent_blockhash)

    # Sign the transaction
    transaction.sign(from_keypair)

    # Send the transaction
    try:
        result = client.send_transaction(transaction, from_keypair)
        print(f"Transaction sent: {result}")
        return result
    except Exception as e:
        print(f"Error sending transaction: {str(e)}")
        return None


# if __name__ == "__main__":
#     data = get_token_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")
#     print(data)
#
#     result = get_result()
#     print(result)

    # resp = send_sol("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq","HFC9JZVhr5QPBJ6fwFZcuJ4zKuwam9rjgQXaTBP5rj5x",0.006)
    # print(resp)
    # print(resp.value)
    # bal = get_wallet_balance("HFC9JZVhr5QPBJ6fwFZcuJ4zKuwam9rjgQXaTBP5rj5x")
    # print(bal)