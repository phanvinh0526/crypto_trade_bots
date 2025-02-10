import asyncio
import logging, time
import re
import requests, json
from datetime import datetime, timedelta

from aiogram import types, Dispatcher, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage
from aiogram.client.default import DefaultBotProperties

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solana.rpc.types import MemcmpOpts


# ###### DESCRIPTION ###### #
# This bot is to search for new token launch from GMGN.AI
# Then validate top holders to predict if the token has a chance to be a big game in near future
# Process:
#   1.  Get CA from GMGN.AI (Smart Money bot scan)
#   2.  Get first 100 trades
#   3.  Filter wallets from those trades, and check number of tokens hold in each wallets
#   4.  If first 100 trades occupy <= 30% token
#   AND their portfolio has a single token => Confirm MMGame
#-------------------------#

# CREDENTIALS
TELE_BOT_TOKEN     = "7406444343:AAFLwMumktwFhhfFSB3uzJXGNTQlLudDGJ8"
BIRDEYE_API_TOKEN  = "6af62e0ddb424d288693b68e3c72805e"
ALCHEMY_API_TOKEN  = "8lkJ9fP65TFrEXHYY_M6eoc_cxjGZ1IX"

# APIs
headers = {
    "x-chain": "solana",
    "X-API-KEY": BIRDEYE_API_TOKEN
}
birdeye_endpoint = "https://public-api.birdeye.so/"


# Constants
TAR_FORUM_ID = -1002229815206
TAR_TOPIC_ID = 5795

# Setup logging
logging.basicConfig(level=logging.INFO)

# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= TELE_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)

# ############## #
# Command handlers
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is about to find a potential token from GMGN.AI bot.'
    )

@dp.message(Command('send_msg_to_topic'))
async def cmd_send_to_topic(msg: types.Message) -> None:
    await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, text=msg.text)
    await msg.reply("Msg sent to the a forum topic!")
    

# ############## #
# Message handlers
# ############## #
# Message handlers
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # local variables
    token_info = {}
    first_trades = []
    total_market_maker = 0
    total_token_holding = 0
    total_token_holding_percentage = 0.0
    start_time = time.time()

    # clean and extract info
    print("Start...")
    msg_data = clean_n_extract(msg.text)

    # check if tokken has been created in an hour
    token_info = get_token_creation_info(msg_data["token_address"])
    # time_difference = calculate_time_difference(token_info["blockUnixTime"])
    # if(time_difference.seconds >= 7200): # if longer than 2hr
    #     return

    # get token overview (eg: symbol, description)
    data = get_token_overview(msg_data["token_address"])
    if(data == {}): # token's liquidity has been withdrawn from the pool
        return
    token_info.update(data)

    # get all market list
    token_info.update(get_token_market(msg_data["token_address"]))
    # get first 20 trades
    first_trades = get_first_trades(token_info["pair_address"], 20)

    # check if buy wallet has more than 10 transactions in the past
    for idx, trade in enumerate(first_trades):
        data = {}
        # This API call takes a lot of time to proceed! TODO: 
        print(f"Checking buyer wallet [{idx}]....")
        data["is_market_maker"] = 0 if get_num_tx_per_wallet(trade["tx_buyer_wallet"]) >= 5 else 1
        total_market_maker += data["is_market_maker"] 
        total_token_holding += trade["tx_token_amt"]
        first_trades[idx].update(data)

    # calculate percentage of first 50 trade bought
    total_token_holding_percentage = round(total_token_holding / 10e8) * 100
    print(f"Top 20 trades holding: {total_token_holding_percentage}%")
    print(f"How many out of 20 are market makers: {total_market_maker}")

    # indicator
    if(total_token_holding_percentage <= 0.3 and total_market_maker >= 5):
        print(f"Suggest to buy token: {msg_data['token_address']}")

    # Response
    # await send_message_to_tradebot(ca_token)
    # await forward_message_to_a_forum(msg)
    await msg.reply(f"{msg_data['token_address']}")
    await msg.reply(f"Total_token_holding_percentage: {total_token_holding_percentage} \n Total_market_maker: {total_market_maker}")

    # logging
    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print(f"***** Elapsed time: {elapsed_time} seconds *****")



# ######## #
# Functions
def get_num_tx_per_wallet(wallet_add: str) -> int:
    url = birdeye_endpoint + "v1/wallet/tx_list" + "?" + f"wallet={wallet_add}" + "&limit=5"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)
    return len(res["data"]["solana"])

def get_first_trades(pair_ca: str, limit: int) -> list:
    url = birdeye_endpoint + "defi/txs/pair" + "?" + f"address={pair_ca}" + f"&limit={limit}&tx_type=swap&sort_type=asc"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)
    lst = []
    for item in res["data"]["items"]:
        data = {}
        data["tx_hash"] = item["txHash"]
        data["tx_time"] = item["blockUnixTime"]
        data["tx_buyer_wallet"] = item["owner"]
        data["tx_sol_amt"] = item["from"]["uiAmount"]
        data["tx_token_amt"] = round(item["to"]["uiAmount"])
        price = item["to"]["price"] if item["to"]["price"] is not None else 0
        data["tx_at_market_cap"] = round(price * 10e8) # as defaul: 1B token created
        lst.append(data)
    return lst

def get_token_market(ca: str) -> dict:
    url = birdeye_endpoint + "defi/v2/markets" + "?" + f"address={ca}" + "&sort_by=liquidity&sort_type=desc&limit=1"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)
    res = res["data"]["items"][0]
    data = {}
    data["pair_address"] = res["address"]
    data["pair_name"] = res["name"]
    data["pair_source"] = res["source"]
    data["liquidity"] = round(res["liquidity"])
    data["unique_wallet_24h"] = res["uniqueWallet24h"]
    return data

def get_token_overview(ca: str) -> dict:
    url = birdeye_endpoint + "defi/token_overview" + "?" + f"address={ca}"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)
    if(res["data"] == {}):
        return {}
    data = {}
    data["address"] = res["data"]["address"]
    data["decimals"] = res["data"]["decimals"]
    data["symbol"] = res["data"]["symbol"]
    data["name"] = res["data"]["name"]
    # data["description"] = res["data"]["extensions"]["description"]
    return data

def calculate_time_difference(unix_time) -> int:
    unix_time_dt = datetime.fromtimestamp(unix_time)
    current_time = datetime.now()
    return current_time - unix_time_dt

def get_token_creation_info(ca: str) -> dict:
    url = birdeye_endpoint + "defi/token_creation_info" + "?" + f"address={ca}"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)
    if(res["success"] == True):
        return res["data"]
    else:
        return None

def clean_n_extract(text: str) -> dict:
    data = {}
    
    # Extract Smart Money Buy URL
    buy_url = re.search(r'Smart Money Buy .* \((https://gmgn\.ai/sol/token/[a-zA-Z0-9]+)\)', text)
    data['buy_url'] = buy_url.group(1) if buy_url else None
    
    # Extract Inflow
    inflow = re.search(r'Smart Inflow净流入:\$\s?(-?\d+\.?\d*)\s?\((-?\d+\.?\d*)\s?Sol\)', text)
    data['inflow_usd'] = inflow.group(1) if inflow else None
    data['inflow_sol'] = inflow.group(2) if inflow else None
    
    # Extract Smart Buy/Sell
    buy_sell = re.search(r'Smart Buy/Sell:(\d+)/(\d+)', text)
    data['smart_buy'] = buy_sell.group(1) if buy_sell else None
    data['smart_sell'] = buy_sell.group(2) if buy_sell else None
    
    # Extract Token Address
    token_address = re.search(r'([a-zA-Z0-9]{32,44})', text)
    data['token_address'] = token_address.group(1) if token_address else None
    
    # Extract 5m TXs/Vol
    txs_vol = re.search(r'5m TXs/Vol:(\d+)/\$(\d+\.?\d*K)', text)
    data['txs_5m'] = txs_vol.group(1) if txs_vol else None
    data['vol_5m'] = txs_vol.group(2) if txs_vol else None
    
    # Extract FDV Market Cap
    fdv_market_cap = re.search(r'FDV市值:\$(\S*)', text)
    data['fdv_market_cap'] = fdv_market_cap.group(1) if fdv_market_cap else None
    
    # Extract Chart URL
    chart_url = re.search(r'Chart看K线 \((https://gmgn\.ai/sol/token/[a-zA-Z0-9]+)\)', text)
    data['chart_url'] = chart_url.group(1) if chart_url else None
    
    # Extract Cost
    cost = re.search(r'Cost成本\$(\d+\.?\d*)', text)
    data['cost'] = cost.group(1) if cost else None
    
    # Extract Holding
    holding = re.search(r'Holding持仓\s([\S*]+[MKB]?)\/\$([\S*]+)\(([\d.]+)\sSol\)', text)
    data['holding_amount'] = holding.group(1) if holding else None
    data['holding_usd'] = holding.group(2) if holding else None
    data['holding_sol'] = holding.group(3) if holding else None
    
    # Extract Holder Address
    holder_address = re.search(r'\((https://gmgn\.ai/sol/address/[a-zA-Z0-9]+)\)', text)
    data['holder_address'] = holder_address.group(1) if holder_address else None

    return data

def validate_ca(ca_token: str) -> str:
    # If can in the list below, will not return
    blacklist = ['H7bTHGb5Cvo5fGe5jBDNDPUv8KykQnzyZA3qZ8sH7yxw','CQbXk942c6GPcRwtZ2WMFP5JcQ9NqbXtb8jUewBi7GoT']
    if ca_token in blacklist:
        return '1'
    else:
        return ca_token

async def forward_message_to_a_forum(msg: types.Message) -> None:
    await bot.forward_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)
    await msg.reply("Message forwarded!")

# ######## #
# Main Funcs
async def main() -> None:
    """The main function which will execute our event loop and start polling"""
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# ### Test Case ### #
