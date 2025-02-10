import asyncio
import logging
import re
import requests
from aiogram import types, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.methods import SendMessage

from bot_creation.bot_instance import bot_search_ca_in_text

# ###### HOW TO USE###### #
# 1.1 Setup forwarder bot to forward Tg messages to this bot (Vp_Search_Ca_In_Text_bot) 
# 1.2 Setup Twitter2Telegram Tweet to forward new tweet from tracked X account, and forwader bot to this bot (Eg: Perm_Search_CA_In_Text_01)
#   +   Need to add header in forwarder bot (eg: tracking_indicator )
# 3.  The bot will search for the CA, and send it to
#   +   Trojan on Solana
#   +   Internal group for 2nd Trojan bot
# 4.  It will forward the text message to the forum/topic for tracking purpose
#-------------------------#


# Constants
TAR_TRADE_BOTS = -4280440059
TAR_FORUM_ID = -1002229815206
TAR_TOPIC_ID = 5310

# Setup logging
logging.basicConfig(level=logging.INFO)

# Dispatcher
dp = Dispatcher()
bot = bot_search_ca_in_text

# ############## #
# Command handlers
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(
        text='This bot is about to search for Contract Address from a text or url.'
    )

@dp.message(Command('send_msg_to_topic'))
async def cmd_send_to_topic(msg: types.Message) -> None:
    await bot.send_message(chat_id=TAR_FORUM_ID, message_thread_id=TAR_TOPIC_ID, text=msg.text)
    await msg.reply("Msg sent to the a forum topic!")
    
# @dp.message(Command('send_msg_to_bot')) # TODO: not working, have to use Bot Forwarder
# async def cmd_send_msg_to_bot(msg: types.Message) -> None:
#     await bot.send_message(chat_id=4180509096, text=msg.text)
#     await msg.reply(f"Message sent: {msg.text}")


# ############## #
# Message handlers
@dp.message()
async def message_handler(msg: types.Message) -> None:
    found_ca = False
    ca_token = ''
    # Search CA from a text
    ca_token = search_ca(msg.text)
    if len(ca_token) >= 1:
        ca_token = validate_ca(ca_token[0])
        found_ca = True

    # Search CA from a URL
    urls = find_urls(msg.text)
    for url in urls:
        full_url = get_full_url(url)
        tmp_ca_token = search_ca(full_url)
        if len(tmp_ca_token) >= 1:
            ca_token = validate_ca(tmp_ca_token[0])
            found_ca = True

    # Response
    if found_ca == True:
        await send_message_to_tradebot(ca_token)
        await forward_message_to_a_forum(msg)
        await msg.reply(f"Found CA_TOKEN: {ca_token}")



# ######## #
# Functions
def find_urls(text: str):
    url_pattern = re.compile(r'(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])')
    urls = re.findall(url_pattern, text)
    urls_resp = []
    for url in urls:
        url = url[0] + "://" + ''.join(url[1:])
        urls_resp.append(url)
    return urls_resp


def get_full_url(short_url):
    try:
        res = requests.get(short_url)
        full_url = res.url
        return full_url
    except requests.RequestException as e:
        print(f"An error occured in get_full_url: {e}")
        return None
    
def search_ca(text: str) -> list:
    return re.findall('[A-Za-z0-9]{42,46}', text)

def validate_ca(ca_token: str) -> str:
    # If can in the list below, will not return
    blacklist = ['H7bTHGb5Cvo5fGe5jBDNDPUv8KykQnzyZA3qZ8sH7yxw','CQbXk942c6GPcRwtZ2WMFP5JcQ9NqbXtb8jUewBi7GoT']
    if ca_token in blacklist:
        return '1'
    else:
        return ca_token


async def send_message_to_tradebot(token: str) -> None:
    await bot.send_message(chat_id=TAR_TRADE_BOTS, text=token)

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
