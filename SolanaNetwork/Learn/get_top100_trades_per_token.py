import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solana.rpc.types import MemcmpOpts

### CONSTANTS ###
MAINNET_SOL_EP = "https://solana-mainnet.g.alchemy.com/v2/8lkJ9fP65TFrEXHYY_M6eoc_cxjGZ1IX"

# unable to confirm transaction: 2aGEcz27cCxz3A4tc99fS8M4HEMTw9TAyywKumyQoC7FuQY74RSSiixBXUB5UhSzqrSee8Z71MpvarcupmoZdY4U

### FUNCTIONS ###
# get first 100 transactions of a given token account
async def get_first_buyers(token_mint_address: str, limit: int = 2):
    async with AsyncClient(endpoint = MAINNET_SOL_EP) as client:
        token_pubkey = Pubkey.from_string(token_address)
        
        # Fetch the first 100 transaction signatures
        transaction_signatures_response = await client.get_signatures_for_address(token_pubkey, limit=limit)
        transaction_signatures = transaction_signatures_response.value
        
        first_buyers = []
        
        for tx in transaction_signatures:
            # Fetch transaction details
            tx_details_response = await client.get_transaction(tx_sig=tx.signature, max_supported_transaction_version=0)
            tx_details = tx_details_response.value
            
            if tx_details is not None and 'meta' in tx_details:
                meta = tx_details['meta']
                if meta is not None and 'postTokenBalances' in meta:
                    post_token_balances = meta['postTokenBalances']
                    
                    for balance in post_token_balances:
                        if balance['mint'] == token_mint_address:
                            owner_pubkey = balance['owner']
                            if owner_pubkey not in first_buyers:
                                first_buyers.append(owner_pubkey)
                                if len(first_buyers) >= limit:
                                    return first_buyers
        
        return first_buyers

# Replace with your token address
token_address = "J2JQqdAxh4MLyW5Vi9qKu69dzZZWBT65P6LPwGDnpump"

# Run the function and fetch transactions
async def main():
    transactions = await get_first_buyers(token_address)
    
    # Print transaction details
    for tx in transactions:
        print(tx)


# Run the async main function
asyncio.run(main())
