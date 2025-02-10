

from solana.rpc.api import Client
from solders.pubkey import Pubkey

QUICKNODE_TOKEN = "0127af86093591fd3e6926f99a9c4e6a762dce8a"

BAKED_TOKEN = "CQbXk942c6GPcRwtZ2WMFP5JcQ9NqbXtb8jUewBi7GoT"

MY_WALLET = "9L8c5UVf6ERYbxNK3R4JxqgqNgzRMwwzFG7Ngc8SaFyC"

solana_client = Client(f"https://blissful-greatest-liquid.solana-devnet.quiknode.pro/{QUICKNODE_TOKEN}/")

print(solana_client.get_balance(Pubkey.from_string(f'{MY_WALLET}')))

# print(solana_client.get_token_largest_accounts(Pubkey.from_string(f'{MY_WALLET}')))

print(solana_client.get_blocks(0, 10))



# solana balance 9L8c5UVf6ERYbxNK3R4JxqgqNgzRMwwzFG7Ngc8SaFyC -u mainnet-beta