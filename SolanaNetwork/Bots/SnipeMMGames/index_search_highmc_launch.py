import asyncio
import logging
import re
from aiogram import types, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage

from bot_creation.bot_instance import bot_x_with_top_followings


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


# Constants
TAR_FORUM_ID = -1002229815206
TAR_TOPIC_ID = 5168

# https://t.me/c/2229815206/5168

# Setup logging
logging.basicConfig(level=logging.INFO)

# Dispatcher
dp = Dispatcher()
bot = bot_x_with_top_followings

# ############## #
# Command handlers
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is about to search for potential followings of a given X account.'
    )

@dp.message(Command('send_msg_to_topic'))
async def cmd_send_to_topic(msg: types.Message) -> None:
    await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, text=msg.text)
    await msg.reply("Msg sent to the a forum topic!")
    

# ############## #
# Message handlers
@dp.message()
async def message_handler(msg: types.Message) -> None:
    # Translate Watch Account alert
    if re.search("Watched Account:", msg.text):
        lst = re.split('\\n', msg.text)
        len_lst = len(lst)
        v_who = re.findall('\((.*?)\)',lst[0])[0]
        v_following = re.findall('\((.*?)\)',lst[1])[0]
        # find the CA / Token symbol in the Bio
        v_lst = re.findall("([A-Za-z0-9$]+)", ' '.join(lst[2:]))
        v_ca = max(v_lst, key=len) if len(max(v_lst, key=len))==44 else ''
        v_token = re.findall("\$([A-Za-z0-9]+)", ' '.join(lst[2:]))
        v_token = v_token[0] if len(v_token) >= 1 else ''
        v_followers = int(re.split(':', lst[len_lst-3])[1])
        v_following = int(re.split(':', lst[len_lst-2])[1])
    
    # Filter relevant accounts to keep track
    # 1.    having number of followers >= 10k   OR
    # 2.    found CA / $TOKEN in the Bio        OR
    # 3.    Having multiple connections followed this account (Eg: 3 known accts followed) | TODO: Twitter API Sub
        if v_followers >= 10000:
            await forward_message_to_a_group(msg)
            await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, text="Severity: Medium")
        elif v_ca != '' or v_token != '':
            await forward_message_to_a_group(msg)
            await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, text="Severity: Low")


# ######## #
# Functions
async def forward_message_to_a_group(msg: types.Message) -> None:
#    await bot.forward_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, from_chat_id=msg.chat.id, message_id=msg.message_id)
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
# 👤 Watched Account: Shibo (@GodsBurnt (https://twitter.com/GodsBurnt))
# 👀 Now Follows: 🌋铜锣湾happy哥🔥㊙️ (@bazingahappy (https://twitter.com/bazingahappy))
# 📔 Bio: Darkfarms maxi🫶 True Bome Lover 🇨🇳 than BTC 任何分享，都不构成投资建议！DYOR. Not financial advice.
# 👥 Followers: 85463
# 📈 Following: 2551
# 🔑Protected: No
