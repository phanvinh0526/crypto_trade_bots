import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solana.rpc.types import MemcmpOpts

### CONSTANTS ###
MAINNET_SOL_EP = "https://solana-mainnet.g.alchemy.com/v2/8lkJ9fP65TFrEXHYY_M6eoc_cxjGZ1IX"


### FUNCTIONS ###
# get balance of a wallet (unit: sol)
async def get_wallet_balance(wallet_address: str):
    # open a connection
    async with AsyncClient(endpoint = MAINNET_SOL_EP) as client:
        wallet_pubkey = Pubkey.from_string(wallet_address)

        # fetch the SOL balance
        sol_bal_res = await client.get_balance(wallet_pubkey)
        sol_bal = sol_bal_res.value / 10**9 # convert lamports to SOL
        
        return sol_bal


async def get_wallet_portfolio(wallet_address: str):
    async with AsyncClient(endpoint = MAINNET_SOL_EP) as client:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        
        # Fetch the SOL balance
        sol_balance_response = await client.get_balance(wallet_pubkey)
        sol_balance = sol_balance_response.value / 10**9  # Convert lamports to SOL
        
        # Fetch token accounts associated with the wallet
        token_accounts_response = await client.get_token_accounts_by_owner(wallet_pubkey, {"programId": str(Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))})
        token_accounts = token_accounts_response['result']['value']
        
        portfolio = {
            "SOL": sol_balance,
            "tokens": []
        }
        
        # Fetch the balance of each token account
        for token_account_info in token_accounts:
            account_pubkey = Pubkey.from_string(token_account_info['pubkey'])
            account_data_response = await client.get_token_account_balance(account_pubkey)
            account_data = account_data_response['result']['value']
            token_address = token_account_info['account']['data']['parsed']['info']['mint']
            
            portfolio["tokens"].append({
                "token_address": token_address,
                "balance": account_data['uiAmount']
            })
        
        return portfolio


# Run the function and fetch the portfolio
async def main():
    # Replace with your wallet address
    wallet_address = "9L8c5UVf6ERYbxNK3R4JxqgqNgzRMwwzFG7Ngc8SaFyC"

    # get balance in sol
    balance = await get_wallet_balance(wallet_address)
    print(balance)

    # extract holding token in portfolio
    portfolio = await get_wallet_portfolio(wallet_address)
    print(portfolio)

# Run the async main function
asyncio.run(main())
