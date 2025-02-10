import asyncio
import logging, time
import re, json, os
from datetime import datetime, timedelta

from aiogram import types, Dispatcher, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage
from aiogram.client.default import DefaultBotProperties

import psycopg2
from psycopg2 import sql

# ###### HOW TO USE###### #
# 1.  Setup Twitter2Telegram bot to track new followings of a X account
# 2.  Setup forwarder bot to forward alert to this bot (Vp_X_Top_Followings_Bot)
# 3.  Run the bot
# 4.  Once the conditions matched, alert will be forwarded to the Forum/Topic
#-------------------------#

# CREDENTIALS
TELE_BOT_S_WALLET_TRACKING_TOKEN     = os.environ['TELE_BOT_S_WALLET_TRACKING_TOKEN']

# Connect to PostgresDb
DATABASE_URL = os.environ['DATABASE_URL']

# Constants


# Setup logging
logging.basicConfig(level=logging.INFO)

# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= TELE_BOT_S_WALLET_TRACKING_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)

# ############## #
# Command handlers
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is about to extract information from Solana Wallet Tracker bot.'
    )


# ############## #
# Message handlers
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # the function will filter out those text matched to the re pattern
    pattern_01 = "\\n([A-Za-z0-9 ]+): (\+[0-9.,]+) \(\$([0-9.,]+)\)"
    pattern_02 = "\\n([A-Za-z0-9 ]+): (\+[0-9.,]+)"

    # extract the trade value
    try:
        trade_info = re.search(pattern=pattern_01, string=msg.text)
        if(trade_info is None):
            trade_info = re.search(pattern=pattern_02, string=msg.text)

        if(len(trade_info.groups()) == 3):
            trade_value  = trade_info.group(3) if trade_info else None
            trade_value  = trade_value.replace(',', '')
            if(float(trade_value) <= 10.0):
                return
        elif(len(trade_info.groups()) == 2):
            return
        
        # Extract trade information
        trade_info = extract_trade_info(msg.text)
        # Add new record to the database
        add_record_to_db(DATABASE_URL, "wallet_tracking_info", trade_info)

    except Exception as e:
        await msg.reply(f"ERROR: {e}")


# ######## #
# Functions
def extract_trade_info(text):
    # Regular expressions to match the relevant parts of the text
    wallet_pattern = r"\n([A-Za-z0-9]+) \((.*?)\)"
    balance_change_pattern = r"\n([A-Za-z0-9]+): ([+-]?[0-9.,]+) \(\$([+-]?[0-9,.]+)\)"
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
            'INSERT INTO {table} ({fields}) VALUES ({placeholders})'
        ).format(
            table = sql.Identifier(tbl_name),
            fields = sql.SQL(', ').join(map(sql.Identifier, columns)),
            placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )

        # Exec sql query
        cursor.execute(insert_statement, list(values))

        # Commit transaction
        conn.commit()
        print("***Trade info has been added to db.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error while connecting to PostgreSql: {error}") 
    finally:
        # Close the db connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ######## #
# Main Funcs
async def main() -> None:
    """The main function which will execute our event loop and start polling"""
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


# ### Test Case ### #
# V P, [14/7/2024 11:02 AM]
# 💸 TRANSFER (https://solscan.io/tx/Y8eXFyEGBmBPhaN6Z97PWP5eYXPLdjYpJ8xGyVzKK2wVncnK24SzjM4gQ9Y7fyjENqWd2EvnRqcKfW8Gnqpr2M7) on PHANTOM
# 4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm (Celebrity_Exp_Trader_01)

# GJAy...S62h (https://solscan.io/account/GJAyWtBrbfDWwt5azEzuRZVSpiNg7cgCZQ2dmHzyS62h) transferred 49 cult to 🔹Celebrity_Exp_Trader_01 (https://solscan.io/account/4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm).

# 🔹Celebrity_Exp_Trader_01 (https://solscan.io/account/4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm):
# cult (https://solscan.io/token/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos): +49 ($0.03)

# 🔗 cult (MC: $518.27K): BE (https://birdeye.so/token/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos?chain=solana) | DS (https://dexscreener.com/solana/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | DT (https://www.dextools.io/app/en/solana/pair-explorer/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | PH (https://photon-sol.tinyastro.io/en/lp/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | Bullx (https://bullx.io/terminal?chainId=1399811149&address=GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos&r=IXFHAMJ1FN9)
# GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos

# V P, [14/7/2024 11:41 AM]
# ❓ UNKNOWN (https://solscan.io/tx/4LsCDL8r75mp4qChn661tex3Vf3rWPRTbin5W4R7QcLRCkZAMzQmvKuEsUJABoUbqm8bHGiNVjdrpPs1osAzzQAq) on UNKNOWN
# C7ngguPkSpp2uAB5AvoXPfmvMHB3gJFUXHHVjv5n3Sxk (Ran's team sniper 01)

# 🔹Ran's team sniper 01 (https://solscan.io/account/C7ngguPkSpp2uAB5AvoXPfmvMHB3gJFUXHHVjv5n3Sxk):
# CHILLY (https://solscan.io/token/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA): +1,625 ($2.18)

# 🔗 CHILLY (MC: $1.34M): BE (https://birdeye.so/token/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA?chain=solana) | DS (https://dexscreener.com/solana/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | DT (https://www.dextools.io/app/en/solana/pair-explorer/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | PH (https://photon-sol.tinyastro.io/en/lp/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | Bullx (https://bullx.io/terminal?chainId=1399811149&address=7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA&r=IXFHAMJ1FN9)
# 7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA

# V P, [14/7/2024 11:41 AM]
# ❓ UNKNOWN (https://solscan.io/tx/4cxddcAkNa3iuzakK1yBR15z5iQZ42UedyEBRFVFfXX9uhYERcEjRVtErBUfBgdpeoeX3Xw1QrntDCWCoDWnoduK) on UNKNOWN
# GjRacG5qhTwQfUd5r8qAYdiUEVpArJt1T3VcYJh9SWR4 (Kyle Chasses 01)

# 🔹Kyle Chasses 01 (https://solscan.io/account/GjRacG5qhTwQfUd5r8qAYdiUEVpArJt1T3VcYJh9SWR4):
# CHILLY (https://solscan.io/token/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA): +1,625 ($1.79)

# 🔗 CHILLY (MC: $1.10M): BE (https://birdeye.so/token/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA?chain=solana) | DS (https://dexscreener.com/solana/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | DT (https://www.dextools.io/app/en/solana/pair-explorer/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | PH (https://photon-sol.tinyastro.io/en/lp/7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA) | Bullx (https://bullx.io/terminal?chainId=1399811149&address=7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA&r=IXFHAMJ1FN9)
# 7Akh51JvZDvEi9a5KLHkkEfnajJzqRmnK2jVUvW1XRPA

# V P, [14/7/2024 11:41 AM]
# 💸 TRANSFER (https://solscan.io/tx/Y8eXFyEGBmBPhaN6Z97PWP5eYXPLdjYpJ8xGyVzKK2wVncnK24SzjM4gQ9Y7fyjENqWd2EvnRqcKfW8Gnqpr2M7) on PHANTOM
# 4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm (Celebrity_Exp_Trader_01)

# GJAy...S62h (https://solscan.io/account/GJAyWtBrbfDWwt5azEzuRZVSpiNg7cgCZQ2dmHzyS62h) transferred 49 cult to 🔹Celebrity_Exp_Trader_01 (https://solscan.io/account/4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm).

# 🔹Celebrity_Exp_Trader_01 (https://solscan.io/account/4fTKtDeqgyvphbdgXnA4AgQW67VRuzw6LfzGGCJTnfqm):
# cult (https://solscan.io/token/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos): +49 ($0.03)

# 🔗 cult (MC: $518.27K): BE (https://birdeye.so/token/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos?chain=solana) | DS (https://dexscreener.com/solana/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | DT (https://www.dextools.io/app/en/solana/pair-explorer/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | PH (https://photon-sol.tinyastro.io/en/lp/GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos) | Bullx (https://bullx.io/terminal?chainId=1399811149&address=GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos&r=IXFHAMJ1FN9)
# GsTZWLQFuvuSSXn6dtH1JByKbabbZCAfqndsFfdBGvos

# V P, [14/7/2024 11:41 AM]
# 💸 TRANSFER (https://solscan.io/tx/4CGQNgD6oTTXa3XJga5RMuyB5ZPVENKp2xvNkWucaXhBeXzkQ2H3xfK26Dsho97r2NqFGomJVK5iWzEXv8zD3Ew4) on SOLANA PROGRAM LIBRARY
# F6zTiTZo9Gx3gSXzWgRot7kqWxMdsAmhYCfk5qKuXVZL (Banter Member 01)

# JATM...FRWz (https://solscan.io/account/JATM41inQ4DYh8A6imqymxZ74Pim7WMWKxKutmkjFRWz) transferred 600 aTOOKER to FRLL...WnX8 (https://solscan.io/account/FRLLDB79oe4drRFFaqtP5EEKb5sXegqsWcn3zsWaWnX8).

# 🔹Banter Member 01 (https://solscan.io/account/F6zTiTZo9Gx3gSXzWgRot7kqWxMdsAmhYCfk5qKuXVZL):
# aTOOKER (https://solscan.io/token/Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm): +600

# 🔗 aTOOKER: BE (https://birdeye.so/token/Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm?chain=solana) | DS (https://dexscreener.com/solana/Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm) | DT (https://www.dextools.io/app/en/solana/pair-explorer/Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm) | PH (https://photon-sol.tinyastro.io/en/lp/Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm) | Bullx (https://bullx.io/terminal?chainId=1399811149&address=Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm&r=IXFHAMJ1FN9)
# Fd8djwiAfDTh1uK7AS9e1kTaftQWNfXLYQxHX9pYP1Vm
