import aiohttp
import json
from typing import Optional


async def estimate_sol_for_tokens(
        input_token: str,
        amount: int,
        slippage: int = 50  # 0.5% slippage by default
) -> Optional[float]:

    SOL_MINT = "So11111111111111111111111111111111111111112"
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
                # The outAmount is in lamports, so we convert it to SOL
                return int(data['outAmount']) / 1e9  # 1 SOL = 1e9 lamports
            else:
                print(f"Error fetching quote: {response.status}")
                return None


# Example usage:
async def main():
    # Example: Estimate SOL for 1 USDC (assuming USDC has 6 decimal places)
    USDC_MINT = "9Vv199SR7VKVqbJmM5LoT26ZtC9bzrmqqxE3b4dfrubX"
    usdc_amount = 1000000000

    estimated_sol = await estimate_sol_for_tokens(USDC_MINT, usdc_amount)
    if estimated_sol is not None:
        print(f"Estimated SOL for 1 USDC: {estimated_sol:.9f} SOL")
    else:
        print("Failed to estimate SOL amount")


# Run the example
import asyncio

asyncio.run(main())
