import asyncio
import logging, time
import re
import requests, json
from time import sleep
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
# Process:
#   1.  Setup AutoForwarder to forward all messages to this bot
#   2.  Filter
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
TAR_TOPIC_ID = 6985

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
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # local variables
    token_info = {}
    flag_yn    = False
    start_time = time.time()

    # clean and extract info
    print("Start...")
    msg_data = clean_n_extract(msg.text)
    token_info.update(msg_data)

    # get token overview (eg: symbol, description)
    data = get_token_overview(msg_data["token_address"])
    token_info.update(data)

    # Validate token quality
    if(token_info['fdv_market_cap'] is not None and check_pass_conditions(token_info) == True):
        # await forward_message_to_a_forum(msg)
        await send_message_to_forum(token_info)

    # logging
    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print(f"***** Elapsed time: {elapsed_time} seconds *****")



# ######## #
# Functions
def check_pass_conditions(token: dict) -> bool:
    # FDV between 20k - 50k
    print(f"***fdv_market_cap: {token['fdv_market_cap']}")
    if(token['fdv_market_cap'] >= 20000 and token['fdv_market_cap'] <= 100000):
        return True
    
    return False 
    

def get_token_overview(ca: str) -> dict:
    # sleep(3)
    url = birdeye_endpoint + "defi/token_overview" + "?" + f"address={ca}"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)

    data = {}
    if(res["data"] == {}):
        return {}
    if(check_attribute_available(res["data"])):
        data["sticker"] = res["data"]["symbol"]
        data["sticker_full_name"] = res["data"]["name"]
        data["liquidity"] = round(res["data"]["liquidity"], 2) if res["data"]["liquidity"] is not None else 0
        data["market_cap"] = round(res["data"]["realMc"]) if res["data"]["realMc"] is not None else 0
        data["total_holder"] = res["data"]["holder"] if res["data"]["holder"] is not None else 0
        data["unique_wallet_last_30m"] = format(res["data"]["uniqueWallet30m"], ',') if res["data"]["uniqueWallet30m"] is not None else 0
        data["num_trade_last_30m"] = res["data"]["trade30m"]
        data["num_buy_last_30m"] = res["data"]["buy30m"]
        data["num_markets"] = res["data"]["numberMarkets"]
        data["extensions"] = str(res["data"]["extensions"])
    return data

def clean_n_extract(text: str) -> dict:
    data = {}
    
    # Extract Inflow
    inflow = re.search(r'Smart Inflow净流入:\$\s?(-?\d+\.?\d*)\s?\((-?\d+\.?\d*)\s?Sol\)', text)
    data['inflow_usd'] = inflow.group(1) if inflow else None
    data['inflow_sol'] = inflow.group(2) if inflow else None
    
    # Extract Token Address
    token_address = re.search(r'([a-zA-Z0-9]{32,44})', text)
    data['token_address'] = token_address.group(1) if token_address else None
    
    # Extract FDV Market Cap
    fdv_market_cap = re.search(r'FDV市值(.*?)\$(\S*)', text)
    data['fdv_market_cap'] = fdv_market_cap.group(2) if fdv_market_cap else 0
    data['fdv_market_cap'] = string_to_float(data['fdv_market_cap'])

    # Extract FDV Market Cap
    if(data['fdv_market_cap'] == 0):
        fdv_market_cap = re.search(r'MCP(.*?)\$(\S*)', text)
        data['fdv_market_cap'] = fdv_market_cap.group(2) if fdv_market_cap else 0
        data['fdv_market_cap'] = string_to_float(data['fdv_market_cap'])

    return data

def validate_ca(ca_token: str) -> str:
    # If can in the list below, will not return
    blacklist = ['H7bTHGb5Cvo5fGe5jBDNDPUv8KykQnzyZA3qZ8sH7yxw','CQbXk942c6GPcRwtZ2WMFP5JcQ9NqbXtb8jUewBi7GoT']
    if ca_token in blacklist:
        return '1'
    else:
        return ca_token

def check_attribute_available(data: dict):
    lst_att = ["symbol","name","liquidity","realMc","holder","uniqueWallet30m","trade30m","buy30m","numberMarkets","extensions"]
    for att in lst_att:
        if(att not in data.keys()):
            return False
    return True

def string_to_float(s):
    multipliers = {
        'k': 1_000,
        'm': 1_000_000,
        'b': 1_000_000_000,
        't': 1_000_000_000_000
    }
    # Get the last character to determine the multiplier
    suffix = str(s)[-1]
    if suffix.isdigit():
        # No multiplier suffix; directly convert to float
        return float(s)
    else:
        # Extract the numeric part and apply the multiplier
        try:
            num = float(s[:-1])
            multiplier = multipliers.get(suffix.lower(), 1)
            return num * multiplier
        except ValueError:
            raise ValueError(f"Cannot convert '{s}' to float.")

async def send_message_to_forum(token_info: dict) -> None:
    # prepare table data
    res_txt = ""
    for col, val in token_info.items():
        res_txt += str(col).upper() + "   -----   " + str(val) + "\n"
    res_txt += f"https://gmgn.ai/sol/token/{token_info['token_address']}"

    # send messsage
    await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, 
                           text=res_txt, 
                           disable_web_page_preview=True)


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
