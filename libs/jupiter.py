import base58
import base64
import json

from solana.rpc.core import RPCException
from solders import message
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter
import asyncio


# private_key = Keypair.from_bytes(base58.b58decode("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"))  # Replace PRIVATE-KEY with your private key as string
# async_client = AsyncClient("https://api.mainnet-beta.solana.com")
#
# jupiter = Jupiter(
#     async_client=async_client,
#     keypair=private_key,
#     quote_api_url="https://quote-api.jup.ag/v6/quote?",
#     swap_api_url="https://quote-api.jup.ag/v6/swap",
#     open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
#     cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
#     query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
#     query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
#     query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
# )

async def check_transaction_confirmation(async_client, signature, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            response = await async_client.get_signature_statuses([signature])
            if response["result"]["value"][0] is not None:
                confirmation_status = response["result"]["value"][0]["confirmationStatus"]
                if confirmation_status == "confirmed" or confirmation_status == "finalized":
                    print(f"Transaction confirmed after {attempt + 1} attempts!")
                    return True
            print(f"Attempt {attempt + 1}: Transaction not yet confirmed. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            print(f"Error checking confirmation on attempt {attempt + 1}: {str(e)}")
            await asyncio.sleep(retry_delay)

    print(f"Transaction not confirmed after {max_retries} attempts.")
    return False


async def trade(input_token,output_token,amount,slippage):
    key_pair = Keypair.from_bytes(
        base58.b58decode("5bdtULrZt9MaMS7YHk3UP2UMnppe9MbzJAHHCBHWZCTXD6wL9PrTAgN4E3jpxFm6Ew2WfgbdnCGGWJBruRQ5tepq"))

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

            return f"https://explorer.solana.com/tx/{transaction_id}"

            # # Check for transaction confirmation
            # confirmed = await check_transaction_confirmation(async_client, transaction_id)
            #
            # if confirmed:
            #     print("Transaction successfully confirmed!")
            #     # You can add additional logic here for post-confirmation actions
            # else:
            #     print("Failed to confirm transaction within the specified time.")

        except RPCException as rpc_error:
            print(f"RPC Error occurred: {rpc_error.args[0]}")
            print(f"Error message: {rpc_error.args[0].message}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None


# if __name__ == "__main__":
#     asyncio.run(trade("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","So11111111111111111111111111111111111111112", 774400, 100))

