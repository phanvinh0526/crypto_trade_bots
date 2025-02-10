import asyncio
import logging, time
import re
import os
import psycopg2
from psycopg2 import sql

from aiogram import types, Dispatcher, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage
from aiogram.client.default import DefaultBotProperties

# ###### DESCRIPTION ###### #
# This bot is to search for new pool from Bonkbot bot
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

# CREDENTIALS
TELE_BOT_TOKEN = os.environ['TELE_BOT_TOKEN']

# Connect to PostgresDb
DATABASE_URL = os.environ['DATABASE_URL']

# Constants
TAR_FORUM_ID = os.environ['TAR_FORUM_ID']
TAR_TOPIC_ID = os.environ['TAR_TOPIC_ID']

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
# ############## #
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is to search for new pool from Bonkbot bot.'
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
    start_time = time.time()

    # Extract pool information
    pool_info = extract_pool_info(msg.text)

    # If Mc >= 50k and Liq >= 20k
    if(pool_info['market_cap'] is not None and check_conditions(pool_info) == True):
        # Update pool_info to the DB
        add_record_to_db(DATABASE_URL, "token_pool_info", pool_info)

        # Forward to dedicated Channel
        await forward_message_to_a_forum(msg)

    # logging
    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print(f"***Ticker: {pool_info['ticker']}")
    print(f"***** Elapsed time: {elapsed_time} seconds *****")



# ######## #
# Functions
def check_conditions(token: dict) -> bool:
    # FDV between 20k - 50k
    print(f"***Market_Cap: {token['market_cap']}") # Market_Cap: 887.3k / Liquidity_Pool_Value: 56.4k
    if(token['market_cap'] >= 50000 and token['liquidity_pool_value'] >= 20000):
        return True
    return False 


def extract_pool_info(text: str) -> dict:
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
        'ca': mint.group(1) if mint else None,
        'ticker': ticker.group(1) if ticker else None,
        'token_name': name.group(1) if name else None,
        'description': description.group(1).strip() if description else None,
        'renounced_yn': "YES" if renounced and renounced.group(1) == r"✅" else "No",
        'burned_yn': "YES" if burned and burned.group(1) == r"✅" else "No",
        'freeze_yn': freeze.group(1) if freeze and freeze else "No",
        # 'Creator Distribution': creator_distribution.group(1) if creator_distribution else None,
        'top_5_holder_percent': top5_distribution.group(1) if top5_distribution else None,
        'top_20_holder_percent': top20_distribution.group(1) if top20_distribution else None,
        'market_cap': string_to_float(market_cap.group(1)) if market_cap else None,
        'liquidity_pool_value': string_to_float(liquidity_pool_value.group(1)) if liquidity_pool_value else None,
        "dex_url": f"https://dexscreener.com/solana/{mint.group(1) if mint else None}",
        "photon_url": f"https://photon-sol.tinyastro.io/en/lp/{mint.group(1) if mint else None}"
    }


def add_record_to_db(db_url: str, tbl_name: str, data: dict):
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
            'INSERT INTO {table} ({fields}) VALUES ({placeholders}) ON CONFLICT on CONSTRAINT token_pool_info_pk DO NOTHING'
        ).format(
            table = sql.Identifier(tbl_name),
            fields = sql.SQL(', ').join(map(sql.Identifier, columns)),
            placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columns))
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
    await bot.forward_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)


# ######## #
# Main Funcs
async def main() -> None:
    """The main function which will execute our event loop and start polling"""
    # Start polling
    print("Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())