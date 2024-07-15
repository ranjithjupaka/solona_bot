from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.publickey import PublicKey

def create_wallet():
    # Generate a new Solana keypair
    keypair = Keypair.generate()
    public_key = keypair.public_key
    secret_key = keypair.secret_key

    return public_key, secret_key

def get_wallet_balance(public_key_str):

    client = Client("https://api.mainnet-beta.solana.com")
    public_key = PublicKey(public_key_str)
    balance = client.get_balance(public_key)['result']['value']
    balance_sol = balance/1000000000

    return balance_sol

if __name__ == "__main__":
    public_key, secret_key = create_wallet()
    print(f"Public Key: {public_key}")
    print(f"Secret Key: {secret_key.hex()}")

    balance = get_wallet_balance(public_key)
    print(f"Wallet Balance: {balance} lamports")