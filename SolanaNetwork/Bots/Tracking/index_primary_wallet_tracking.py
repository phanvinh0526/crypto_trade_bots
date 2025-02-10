import asyncio
import logging, time
import re, json
from datetime import datetime, timedelta

from aiogram import types, Dispatcher, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage
from aiogram.client.default import DefaultBotProperties

# ###### HOW TO USE###### #
# 1.  Setup Twitter2Telegram bot to track new followings of a X account
# 2.  Setup forwarder bot to forward alert to this bot (Vp_X_Top_Followings_Bot)
# 3.  Run the bot
# 4.  Once the conditions matched, alert will be forwarded to the Forum/Topic
#-------------------------#

# CREDENTIALS
TELE_BOT_P_WALLET_TRACKING_TOKEN     = "7126857633:AAHllGZPoAJWE8qPDAD47cCM-6hy7SGG848"

# Constants
TAR_FORUM_P_WALLET_TRACKING_ID = -1002229815206
TAR_TOPIC_P_WALLET_TRACKING_ID = 6295

# Setup logging
logging.basicConfig(level=logging.INFO)

# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= TELE_BOT_P_WALLET_TRACKING_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)

# ############## #
# Command handlers
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is about to extract information from Solana Wallet Tracker bot.'
    )

@dp.message(Command('send_msg_to_topic'))
async def cmd_send_to_topic(msg: types.Message) -> None:
    await bot.send_message(chat_id=TAR_FORUM_P_WALLET_TRACKING_ID, message_thread_id=TAR_TOPIC_P_WALLET_TRACKING_ID, text=msg.text)
    await msg.reply("Msg sent to the a forum topic!")
    

# ############## #
# Message handlers
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # the function will filter out those text matched to the re pattern
    pattern_01 = "\\n([A-Za-z0-9]+): (\+[0-9.,]+) \(\$([0-9.,]+)\)"
    pattern_02 = "\\n([A-Za-z0-9]+): (\+[0-9.,]+)"

    # extract the trade value
    try:
        trade_info = re.search(pattern=pattern_01, string=msg.text)
        if(trade_info is None):
            trade_info = re.search(pattern=pattern_02, string=msg.text)

        if(len(trade_info.groups()) == 3):
            trade_ticker = trade_info.group(1) if trade_info else None
            trade_tokens = trade_info.group(2) if trade_info else None
            trade_value  = trade_info.group(3) if trade_info else None
            trade_value  = trade_value.replace(',', '')
            if(float(trade_value) <= 10.0):
                return
        elif(len(trade_info.groups()) == 2):
            return
        # forward msg
        await forward_message_to_a_group(msg=msg)

    except Exception as e:
        await msg.reply(f"ERROR: {e}")


# ######## #
# Functions
async def forward_message_to_a_group(msg: types.Message) -> None:
#    await bot.forward_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)
    await bot.forward_message(chat_id=TAR_FORUM_P_WALLET_TRACKING_ID, message_thread_id=TAR_TOPIC_P_WALLET_TRACKING_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)
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
