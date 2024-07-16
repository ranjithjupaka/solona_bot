import time
import base58
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.transaction import Transaction
from solders.system_program import transfer
from solana.rpc.commitment import Confirmed


def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    secret_key = base58.b58encode(keypair.secret()).decode('ascii')
    # print(public_key,secret_key)
    # return public_key, secret_key
    return "4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD", "5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"


def get_wallet_balance(public_key_str):
    client = Client("https://api.mainnet-beta.solana.com")
    public_key = Pubkey.from_string(public_key_str)
    balance = client.get_balance(public_key)
    balance_sol = balance.value / 1e9
    print(balance_sol)
    return balance_sol


def get_gas_price():
    client = Client("https://api.mainnet-beta.solana.com")
    response = client.get_fee_for_message(Confirmed)
    print(response)
    if response and len(response) > 0:
        # Using the median fee as an estimate
        gas_price_lamports = response[len(response) // 2].prioritization_fee
        gas_price_sol = gas_price_lamports / 1e9
        return gas_price_sol
    else:
        # Fallback to a default value if no fees are returned
        return 0.000005  # 5000 lamports


def get_latest_blockhash(client):
    return client.get_latest_blockhash().value.blockhash


def send_sol(from_secret_key, to_public_key_str, amount_sol):
    client = Client("https://api.mainnet-beta.solana.com")
    from_keypair = Keypair.from_base58_string(from_secret_key)
    print(from_keypair)
    to_public_key = Pubkey.from_string(to_public_key_str)
    amount_lamports = int(amount_sol * 1e9)
    latest_blockhash = get_latest_blockhash(client)
    print(latest_blockhash)
    gas_price = int(get_gas_price() * 1e9)
    transaction_amt = amount_lamports - gas_price

    transaction = Transaction().add(transfer(
        from_pubkey=from_keypair.pubkey(),
        to_pubkey=to_public_key,
        lamports=transaction_amt
    ))

    transaction.recent_blockhash = latest_blockhash
    transaction.sign(from_keypair)

    try:
        response = client.send_transaction(transaction)
        return response
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return None


if __name__ == "__main__":
    # create_wallet()
    solana_client = Client("https://api.mainnet-beta.solana.com")
    # key_pair = Keypair.from_base58_string("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq")
    key_pair = Keypair()
    # bytes_string = bytes(key_pair)[:32]+bytes(key_pair)[32:0]
    # print(bytes_string.hex())
    print(key_pair.secret().decode('utf-8'),key_pair.pubkey())
    # get_wallet_balance("4u7gSZLu9hJf4GhFW9r4tHoTL47PuDwQtJ6euEmGtYWD")

