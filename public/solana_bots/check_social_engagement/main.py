import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

from LunaCrush import LunarCrushSearch, LunarCrushTopicPosts, format_json_for_telegram

# ###### DESCRIPTION ###### #
# This bot is to 
#   1.  measure social impact and display it in Telegram bot
#   
# Process:
#   1.  Call APIs from LunaCrush to retrieve metrics from Twitter
#   2.  Display response in proper formated
#-------------------------#
# Load variables from .env file
load_dotenv()

# CREDENTIALS
VP_CHECK_SOCIAL_ENG_BOT = os.environ['VP_CHECK_SOCIAL_ENG_BOT']

# Setup logging
logging.basicConfig(level=logging.ERROR)

# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= VP_CHECK_SOCIAL_ENG_BOT,
    default=DefaultBotProperties(parse_mode='HTML')
)

# Tele bot states capture
user_states = {}


# ############## #
# Command handlers
# ############## #
@dp.message(Command("start"))
async def start_command_func(msg: types.Message) -> None:
    await msg.answer(
        text="""<b><u>This bot is about to search a CA (Contract Address) on Twitter to measure</u></b>
            + Engagement impact
            + Views
            + Original post this sticker
            + Analyze post widespread on social platform
            + Understand hot topics that sticker creator interested in
        """,
        parse_mode="HTML"
    )

@dp.message(Command("ca_search"))
async def ca_search_command(msg: types.Message) -> None:
    await msg.reply(text="🔍 Please provide a string to search:", parse_mode="HTML")
    user_states[msg.from_user.id] = "awaiting_ca_search_input"   

def ca_search_func(ca_str: str) -> None:
    # Run
    lunarcrush = LunarCrushTopicPosts()
    topic_data = lunarcrush.analyze_topic(ca_str)  # Replace with your topic

    lunarcrush = LunarCrushSearch()
    post_data = lunarcrush.search_post_data(ca_str)

    return format_json_for_telegram(topic_data, post_data)


@dp.message()
async def message_handler(msg: types.Message) -> None:
    user_id = msg.from_user.id

    # check user in 'ca_search' state
    if user_states.get(user_id) == 'awaiting_ca_search_input':
        input_str = msg.text
        await msg.reply(text=ca_search_func(input_str), parse_mode="HTML")
        # clear state
        user_states.pop(user_id, None)



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
