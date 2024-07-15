import time

from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.transaction import Transaction, TransactionInstruction
from solana.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts
from solana.blockhash import Blockhash
from base58 import b58decode


def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair.generate()
    public_key = keypair.public_key
    secret_key = keypair.secret_key
    secret_key = secret_key.hex()

    # return public_key, secret_key
    return "4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD", "5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"


def get_wallet_balance(public_key_str):
    client = Client("https://api.mainnet-beta.solana.com")
    public_key = PublicKey(public_key_str)
    balance = client.get_balance(public_key)['result']['value']
    balance_sol = balance / 1000000000

    return balance_sol


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
    client = Client("https://api.mainnet-beta.solana.com")
    secret_key_bytes = b58decode(from_secret_key)
    from_keypair = Keypair.from_secret_key(secret_key_bytes)
    print(from_keypair)
    to_public_key = PublicKey(to_public_key_str)
    amount_lamports = int(amount_sol * 1000000000)

    latest_blockhash = get_latest_blockhash(client)
    print(latest_blockhash)

    gas_price = int(get_gas_price() * 1000000000)
    transaction_amt = amount_lamports-gas_price

    transaction = Transaction(recent_blockhash=latest_blockhash)
    transfer_instruction = transfer(
        TransferParams(
            from_pubkey=from_keypair.public_key,
            to_pubkey=to_public_key,
            lamports=transaction_amt
        )
    )
    transaction.add(transfer_instruction)
    response = client.send_transaction(transaction, from_keypair, opts=TxOpts(skip_preflight=True))
    return response


# if __name__ == "__main__":
    # resp = send_sol("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq","HFC9JZVhr5QPBJ6fwFZcuJ4zKuwam9rjgQXaTBP5rj5x",0.00699)
    # print(resp)
    # gas_price = get_gas_price()
    # print(f"Gas price: {gas_price} SOL")
