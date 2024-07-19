import base58
import base64
import json
import aiohttp
import json
from typing import Optional

from solana.rpc.core import RPCException
from solders import message
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter
import asyncio
import config
from solona_utils import send_sol

OWNER_ADDRESS = config.OWNER
SOL_MINT = "So11111111111111111111111111111111111111112"


# private_key = Keypair.from_bytes(base58.b58decode("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"))  # Replace PRIVATE-KEY with your private key as string
# async_client = AsyncClient("https://api.mainnet-beta.solana.com")


async def estimate_sol_for_tokens(
        input_token: str,
        amount: int,
        slippage: int = 50
) -> Optional[float]:
    try:
        JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"

        params = {
            "inputMint": input_token,
            "outputMint": SOL_MINT,
            "amount": str(amount),
            "slippageBps": slippage
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(JUPITER_QUOTE_API, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return int(data['outAmount'])
                else:
                    print(f"Error fetching quote: {response.status}")
                    return None
    except Exception as e:
        print('error', e)
        return None


async def trade(private_key, input_token, output_token, amount, slippage):
    print('args----', private_key, input_token, output_token, amount, slippage)
    key_pair = Keypair.from_bytes(base58.b58decode(private_key))

    if input_token == SOL_MINT:
        amount = int(amount * 0.95)
        owner_fees = int(amount * 0.05) / 1000000000
        result = send_sol(private_key, OWNER_ADDRESS, owner_fees)

        if result is None:
            return {'err': True, 'msg': "Try again Sometime later"}
    else:
        estimated_sol = await estimate_sol_for_tokens(input_token, amount)
        owner_fees = int(estimated_sol * 0.05) / 1000000000

        result = send_sol(private_key, OWNER_ADDRESS, owner_fees)

        if result is None:
            return {'err': True, 'msg': "Try again Sometime later"}

    async with AsyncClient("https://api.mainnet-beta.solana.com") as async_client:
        jupiter = Jupiter(
            async_client=async_client,
            keypair=key_pair,
            quote_api_url="https://quote-api.jup.ag/v6/quote?",
            swap_api_url="https://quote-api.jup.ag/v6/swap",
            open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
            cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
            query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
            query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
            query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
        )

        try:
            transaction_data = await jupiter.swap(
                input_mint=input_token,
                output_mint=output_token,
                amount=amount,
                slippage_bps=slippage,
            )
            print('data', transaction_data)

            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = key_pair.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])

            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            print('result', result)

            transaction_id = json.loads(result.to_json())['result']
            print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")

            print("Waiting for transaction confirmation...")

            return {'err': False, 'txid': transaction_id}

            # # Check for transaction confirmation
            # confirmed = await check_transaction_confirmation(async_client, transaction_id)
            #
            # if confirmed:
            #     print("Transaction successfully confirmed!")
            #     # You can add additional logic here for post-confirmation actions
            # else:
            #     print("Failed to confirm transaction within the specified time.")

        except RPCException as rpc_error:
            error_data = rpc_error.args[0]
            print(f"RPC Error occurred: {error_data}")
            print(f"Error message: {error_data.message}")

            error_logs = error_data.data.logs if hasattr(error_data, 'data') and hasattr(error_data.data,
                                                                                         'logs') else []

            if "insufficient lamports" in ' '.join(error_logs).lower():
                insufficient_lamports_log = next((log for log in error_logs if "insufficient lamports" in log.lower()),
                                                 None)
                if insufficient_lamports_log:
                    print("Error: Insufficient SOL balance to complete the transaction.")
                    print(f"Details: {insufficient_lamports_log}")
                    # Extract the required and available lamports
                    parts = insufficient_lamports_log.split()
                    available = int(parts[3].rstrip(','))
                    required = int(parts[5])
                    shortfall = required - available
                    msg = f"You need {shortfall} more lamports (approximately {shortfall / 1e9:.9f} SOL) to complete this transaction."
                    print(msg)
                    return {'err': True, 'msg': msg}

            return {'err': True, 'msg': ''}
        except Exception as e:
            print(f"An error occurred: {e}")

            if "not tradable" in str(e):
                return {'err': True, 'msg': e}

            return {'err': True, 'msg': ''}

# if __name__ == "__main__":
#     result = asyncio.run(
#         trade("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "So11111111111111111111111111111111111111112",
#               50000,
#               50))
#     print(result)
