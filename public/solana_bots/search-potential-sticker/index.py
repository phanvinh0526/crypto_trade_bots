import asyncio
import logging, time
import re
import os
from dotenv import load_dotenv

from aiogram import types, Dispatcher, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage
from aiogram.client.default import DefaultBotProperties

import psycopg2
from psycopg2 import sql

from LunaCrush import LunarCrushSearch, LunarCrushTopicPosts

# ###### DESCRIPTION ###### #
# This bot is to 
#   1.  search for new pool from Bonkbot bot | Solana network
#   2.  search for new pool from Coingecko bot | Ethereum network
#   3.  insert tokens / trades from wallet tracking | Sol network
#   
# Process:
#   1.  Setup AutoForwarder to forward all messages (from: New Pool and Burned topic) to this bot
#   2.  Extract relevant information (eg: Ticker, Name, Description, Renounce, Burned, Freeze, Distributions top10-top20, MC, Liquidity, Mint)
#   3.  Update new pool record into the database
#   4.  If MarketCap >= 50k and Liq >= 20k, forward msg to the dedicated Topic for instant reaction
#   5.  Optional: another bot, to run every 2hr to refresh existing records in DB
#   6.  Optional: build Tableau dashboard to view data in db
#   7.  Optional: measure token performance based on
#       +   Popularity of the CA/Sticker on X
#       +   Number of holders increase overtime
#       +   Number of Telegram subscribers increase overtime
#-------------------------#
# Load variables from .env file
load_dotenv()

# CREDENTIALS
TELE_BOT_SEARCH_NEWPOOL_CRED = os.environ['VP_SEARCH_NEWPOOL_BOT']

# Connect to PostgresDb
DATABASE_URL = os.environ['DATABASE_URL']

# Constants
TAR_FORUM_ID = os.environ['TAR_FORUM_ID']
TAR_TOPIC_ID = os.environ['TAR_TOPIC_ID']

# Setup logging
logging.basicConfig(level=logging.ERROR)


# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= TELE_BOT_SEARCH_NEWPOOL_CRED,
    default=DefaultBotProperties(parse_mode='HTML')
)

# ############## #
# Command handlers
# ############## #
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is to search for new pool from public Channels (Bonkbot, GMGN, ..etc..)'
    )


# ############## #
# Message handlers
# ############## #
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # local variables
    start_time = time.time()

    # Navigator
    nav_chain, nav_channel = navigate_msg(msg.text)
    if nav_chain is None:
        await msg.reply("** Cannot find the navigation header!")
        return
    else:
        pool_info = {}

        # New pool | Sol network
        if nav_chain == 'NewPool_SOL':
            pool_info = extract_pool_info_solana(msg.text, nav_channel)
            # Conditions: If Mc >= 50k and Liq >= 20k
            if(pool_info['market_cap'] is not None and check_sol_conditions(pool_info) == True):
                # 1. Perform Social Engagement check in real-time
                is_potential = False

                # 1.1 Count engagement of the ticker


                # 1.2 Search posts with CA to find the original Tweet, and Creator background


                # 2. Add sticker to Db for batch processing
                add_record_to_db("token_pool_info", pool_info, "ON CONFLICT on CONSTRAINT token_pool_info_pk DO NOTHING")
                await forward_message_to_a_forum(msg)

        # # New pool | Eth network
        # if nav_chain == '$NewPool_ETH$':
        #     pool_info = extract_pool_info_etherium(msg.text)
        #     add_record_to_db("token_pool_info", pool_info, "ON CONFLICT on CONSTRAINT token_pool_info_pk DO NOTHING")
        #     await forward_message_to_a_forum(msg)
            
        # # New trade | Sol network
        # if nav_chain == '$Wallet_Tracking_SOL$':
        #     trade_info = extract_wallet_tracking_sol(msg.text)
        #     add_record_to_db("wallet_tracking_info", trade_info, "")

    # logging
    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print(f"***** Elapsed time: {elapsed_time} seconds *****")



# ######## #
# Functions
def navigate_msg(msg: str) -> str:
    # Define regex patterns for each piece of information
    match = re.search(r"\$(.*?)\$", msg)
    if match:
        resp = match.group(1)
        resp_chain, resp_channel = resp.rsplit("_", 1)
        print(f"Navigator: {resp_chain + '-' + resp_channel}")
        return resp_chain, resp_channel
    return None


def extract_wallet_tracking_sol(msg: str) -> str:
    pattern_01 = "\\n([A-Za-z0-9 ]+): (\+[0-9.,]+) \(\$([0-9.,]+)\)"
    pattern_02 = "\\n([A-Za-z0-9 ]+): (\+[0-9.,]+)"
    # extract the trade value
    try:
        trade_info = re.search(pattern=pattern_01, string=msg)
        if(trade_info is None):
            trade_info = re.search(pattern=pattern_02, string=msg)

        if(len(trade_info.groups()) == 3):
            trade_value  = trade_info.group(3) if trade_info else None
            trade_value  = trade_value.replace(',', '')
            if(float(trade_value) <= 10.0):
                return
        elif(len(trade_info.groups()) == 2):
            return
        
        # Extract trade information
        trade_info = extract_trade_info(msg)
        return trade_info

    except Exception as e:
        print(f"ERROR: in `extract_wallet_tracking_sol` with message {e}")


def extract_pool_info_etherium(msg: str) -> str:
    # Define regex patterns for each piece of information
    p_token_pair = re.search("\$[Recent launch,New trending token]+:\\n([\w\s]+)", msg)
    p_trending   = 'Trending' if re.search("(New trending token)", msg) else None,
    p_address    = re.search("(?<=Address: )0x[a-fA-F0-9]{37,45}", msg)
    p_token_created_at = re.search(r"(?<=Created at: )\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", msg)
    p_market_cap = re.search(r"(?<=Market cap: )\d+(\.\d+)?", msg)

    return {
        'network': "Ethereum",
        'ticker':  str(p_token_pair.group(1).strip()).lower(),
        'token_name': '',
        'ca': str(p_address.group(0)).lower(),
        'created_at': p_token_created_at.group(0),
        'market_cap': p_market_cap.group(0),
        'is_trending': p_trending
    }


def extract_trade_info(text):
    # Regular expressions to match the relevant parts of the text
    wallet_pattern = r"\n([A-Za-z0-9]+) \((.*?)\)"
    balance_change_pattern = r"\n([A-Za-z0-9 ]+): ([+-]?[0-9.,]+) \(\$([+-]?[0-9,.]+)\)"
    token_info_pattern = r"\n([A-Za-z0-9]{42,46})"

    # Extracting the wallet address and name
    wallet_match = re.search(wallet_pattern, text)
    wallet_address = wallet_match.group(1)
    wallet_name = wallet_match.group(2)

    # Extracting the balance changes
    balance_changes = {}
    for match in re.finditer(balance_change_pattern, text):
        currency = match.group(1)
        amount = float(match.group(2).replace(',', ''))
        usd_value = float(match.group(3).replace(',', ''))
        if(currency != 'SOL' and currency != 'USDT' and currency != 'USDC'):
            balance_changes["ticker"] = currency
            balance_changes["ticker_amt"] = amount
            balance_changes["ticker_usd_val"] = usd_value

    # # Extracting token info
    token_info_match = re.findall(token_info_pattern, text)
    token_ca = token_info_match[len(token_info_match)-1]

    # Compiling the extracted information
    return {
        'wallet_address': str(wallet_address).lower(),
        'wallet_name': wallet_name,
        'ticker': str(balance_changes["ticker"]).lower(),
        'ticker_amt': balance_changes["ticker_amt"],
        'ticker_amt_usd': balance_changes["ticker_usd_val"],
        'ticker_ca': str(token_ca).lower()
    }


def check_sol_conditions(token: dict) -> bool:
    # FDV between 20k - 50k
    print(f"***Market_Cap: {token['market_cap']}") # Market_Cap: 887.3k / Liquidity_Pool_Value: 56.4k
    if(token['market_cap'] >= 50000 and token['liquidity_pool_value'] >= 20000):
        return True
    return False 


def extract_pool_info_solana_bonkbot(text: str):
        # Define regular expressions for extracting information
    ticker_pattern = r"Ticker:\s*\$(\w+)"
    name_pattern = r"Name:\s*(.+)"
    description_pattern = r"Description:\s*(.+?)(?=\nRenounced:)"
    renounced_pattern = r"Renounced:\s*(✅|❌)"
    burned_pattern = r"Burned:\s*(✅|❌)"
    freeze_pattern = r"Freeze(?: ❄️)?:\s*(Enabled|Disabled)\s*(✅|❌)"
    # creator_distribution_pattern = r"Creator:\s*([\d.]+%)"
    top5_distribution_pattern = r"Top 5:\s*(?:⚠️)?(\d+)%"
    top20_distribution_pattern = r"Top 20:\s*(?:⚠️)?(\d+)%"
    market_cap_pattern = r"Market Cap:\s*([\d.]+k)\s*USD"
    liquidity_pool_pattern = r"Liquidity Pool value:\s*([\d.]+k)\s*USD"
    mint_pattern = r"Mint:\s*(\w+)"
    
    # Extract information using regex patterns
    ticker = re.search(ticker_pattern, text)
    name = re.search(name_pattern, text)
    description = re.search(description_pattern, text, re.DOTALL)
    renounced = re.search(renounced_pattern, text)
    burned = re.search(burned_pattern, text)
    freeze = re.search(freeze_pattern, text)
    # creator_distribution = re.search(creator_distribution_pattern, text)
    top5_distribution = re.search(top5_distribution_pattern, text)
    top20_distribution = re.search(top20_distribution_pattern, text)
    market_cap = re.search(market_cap_pattern, text)
    liquidity_pool_value = re.search(liquidity_pool_pattern, text)
    mint = re.search(mint_pattern, text)
    
    # Return the extracted information
    return {
        'network': "Solana",
        'ca': str(mint.group(1)).lower() if mint else None,
        'ticker': str(ticker.group(1)).lower() if ticker else None,
        'token_name': str(name.group(1)).lower() if name else None,
        'description': str(description.group(1).strip()).lower() if description else None,
        'renounced_yn': "YES" if renounced and renounced.group(1) == r"✅" else "No",
        'burned_yn': "YES" if burned and burned.group(1) == r"✅" else "No",
        'freeze_yn': freeze.group(1) if freeze and freeze else "No",
        # 'Creator Distribution': creator_distribution.group(1) if creator_distribution else None,
        'top_5_holder_percent': top5_distribution.group(1) if top5_distribution else None,
        'top_20_holder_percent': top20_distribution.group(1) if top20_distribution else None,
        'market_cap': string_to_float(market_cap.group(1)) if market_cap else None,
        'liquidity_pool_value': string_to_float(liquidity_pool_value.group(1)) if liquidity_pool_value else None,
        "dex_url": f"https://dexscreener.com/solana/{mint.group(1) if mint else None}",
        "gmgn_url": f"https://gmgn.ai/sol/token/{mint.group(1) if mint else None}"
    }


def extract_pool_info_solana_gmgn_kol(text: str):
    # 'num_kol_buy' = 5
    # 'token_name' = 'Central African Republic Meme'
    # 'ca' = '7oBYdEhV4GkXC19ZfgAvXpJWp2Rn9pm1Bx2cVNxFpump'
    # 'market_cap' = 36300000.0
    # 'liquidity_pool_value' = 726900.0
    # 'top_10' = 87.61
    data = {}
    # Patterns for extracting values
    patterns = {
        "num_kol_buy": r"(\d+)\s*KOL Buy",  # Extracts only the number
        "token_name": r"\$\w+\(([^)]+)\)", # sticker name
        "ca": r"\n([A-Za-z0-9]{42,46})",  # Matches the full token address
        "market_cap": r"MCP:\s*\$?([\w+\.\,]+)",  # Extracts MCP value with suffix
        "liquidity_pool_value": r"Liq:\s*[\d\.\,]+\s*SOL\s*\(\$([\d\.KMB]+)",  # Extracts liquidity in $
        "top_10": r"TOP 10:\s*(\d+\.\d+%)"  # Extracts TOP 10 value as percentage
    }
    # Extract values using regex
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.groups()
            if key == "market_cap":  
                data[key] = string_to_float(value[0])  # Convert MCP
            elif key == "liquidity_pool_value":
                data[key] = string_to_float(value[0])  # Convert Liquidity
            elif key == "top_10":
                data[key] = float(value[0].replace("%", ""))  # Convert % to float
            else:
                data[key] = int(value[0]) if key == "num_kol_buy" else value[0]
        else:
            data[key] = None
    return data


def extract_pool_info_solana_dexscreener(text: str):
    extracted_data = {}
    # Regular expressions to extract values
    patterns = {
        "fdv": r"FDV:\s*🏛\s*\$([\d,.]+[KM]?)",
        "liquidity": r"Liquidity:\s*💧\s*\$([\d,.]+[KM]?)",
        "age": r"Age:\s*🌿\s*([\d\w]+)",
        "24h_txns_total": r"24H Txns:\s*🔁\s*Total:\s*([\d,.KM]+)",
        "ca": r"📄 CA:\s*([\w\d]+)",
        "price_chg_24h": r"Price Chg:\s*📈\s*24H:\s*🟢\s*([\d,.%]+)",
        "24h_makers_buyers":  r"24H Makers:\s*🥸\s*Total:.*?\n\s*Buyers:\s*([\d,.KM]+)",
        "24h_makers_sellers": r"24H Makers:\s*🥸\s*Total:.*?\n\s*Buyers:.*?\n\s*Sellers:\s*([\d,.KM]+)",
        "now_trending_at": r"is now trending at\s*([\d️⃣]+)"
    }
    # Extract values using regex
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted_data[key] = match.group(1)
        else:
            extracted_data[key] = None
    # Convert "Now trending at" value to a numeric format
    if "Now trending at" in extracted_data:
        numeric_value = re.sub(r"\D", "", extracted_data["Now trending at"])  # Remove non-digit characters
        extracted_data["Now trending at"] = int(numeric_value) if numeric_value.isdigit() else None
    # Respond
    return extracted_data


def extract_pool_info_solana(text: str, nav_channel: str) -> dict:
    # # Bonkbot - search new pool
    # if nav_channel.lower() == 'Bonkbot'.lower():
    #     return extract_pool_info_solana_bonkbot(text)

    # GMGN KOL Fomo - search sticker bought by KOLs
    if nav_channel.lower() == "GmgnKolFomo".lower():
        # Filter: KOL buy between 4 and 5
        match = re.search(r"(\d+)\s*KOL Buy", text)
        if match:
            value = match.group(1)
            if int(value) in (4, 8):
                return extract_pool_info_solana_gmgn_kol(text)
        return {'market_cap': None}
    
    # # Dex Screener to search top 10 token on-trend
    # if nav_channel.lower() == "DexScreener".lower():
    #     return extract_pool_info_solana_dexscreener(text)
    

def add_record_to_db(tbl_name: str, data: dict, constraints=""):
    """
    Inserts a new token pool information into a 'token_pool_info' table in the Heroku PostgreSQL database.

    Parameters:
    - db_url (str): The database connection URL.
    - table_name (str): The name of the table to insert the data into.
    - data (dict): A dictionary where keys are column names and values are the corresponding values to insert.

    Returns:
    - None
    """
    try:
        # Connect to Heroku postgreSql db
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

        # Prepare the Sql query
        columns = data.keys()
        values = data.values()
        insert_statement = sql.SQL(
            'INSERT INTO {table} ({fields}) VALUES ({placeholders}) {constraints}'
        ).format(
            table = sql.Identifier(tbl_name),
            fields = sql.SQL(', ').join(map(sql.Identifier, columns)),
            placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columns)),
            constraints = sql.SQL(constraints)
        )

        # Exec sql query
        cursor.execute(insert_statement, list(values))

        # Commit transaction
        conn.commit()
        print("Token info added to db.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error while connecting to PostgreSql: {error}") 
    finally:
        # Close the db connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
        

async def forward_message_to_a_forum(msg: types.Message) -> None:
    await msg.reply('Token has been added to Db.')
    await bot.forward_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)


# ######## #
# Main Funcs
async def main() -> None:
    """The main function which will execute our event loop and start polling"""
    # Remove pending updates before starting the bot
    await bot.delete_webhook(drop_pending_updates=True)

    # Start polling
    print("Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
