import asyncio, requests
import datetime
import logging
import os
import pytz
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime
from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# ###### DESCRIPTION ###### #
# This bot is to 
#   1.  Keep track big wallets on HyperLiquid DEX
#   2.  Identify insiders / whale orders to suggest Long/Short
#   3.  [Optional] Find 20x+ leverage wallets with position over 500K
#   4.  Present those wallets & trades to Telegram group
#-------------------------#

# Load variables from .env file
load_dotenv()

# CREDENTIALS
VP_CHECK_HYPERLIQUID_BOT = os.environ['VP_CHECK_HYPERLIQUID_BOT']
VP_CRYPTO_GROUP_CHAT_ID = os.environ['VP_CRYPTO_GROUP_CHAT_ID']
VP_CRYPTO_GROUP_CHAT_TOPIC_ID = os.environ['VP_CRYPTO_GROUP_CHAT_TOPIC_ID']
VP_PERIODICAL_CHECK_TIME = int(os.environ['VP_PERIODICAL_CHECK_TIME'])
VP_USER_ADDRESSES = os.environ['VP_USER_ADDRESSES']

# Setup logging
logging.basicConfig(level=logging.ERROR)

# Dispatcher
dp = Dispatcher()
bot = Bot(
    token= VP_CHECK_HYPERLIQUID_BOT,
    default=DefaultBotProperties(parse_mode='HTML')
)

# Variables
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"
USER_ADDRESSES = VP_USER_ADDRESSES.split(',')

# Store the last seen trade ID to avoid duplicates
last_trade_id = None

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

async def fetch_recent_trades(user_address):
    """
    Fetch recent trades for a given wallet address from Hyperliquid API within the last 1 hour.
    """
    end_time = int(datetime.now().timestamp() * 1000)  # Current time in milliseconds
    start_time = end_time - (VP_PERIODICAL_CHECK_TIME * 1000)  # 3 hour ago in milliseconds

    payload = {
        "type": "userFillsByTime",
        "user": user_address,
        "startTime": start_time,
        "endTime": end_time,
        "aggregateByTime": True
    }

    response = requests.post(HYPERLIQUID_API_URL, json=payload)

    if response.status_code != 200:
        print(f"Error fetching trades: {response.status_code}")
        return None

    trades = response.json()
    if not trades:
        return None

    # Aggregating by coin and direction (Buy/Sell)
    trade_summary = defaultdict(lambda: {"total_size": 0, "total_price": 0, "total_pnl": 0, "total_time": 0, "count": 0})

    for trade in trades:
        coin = trade.get("coin", "Unknown")
        direction = trade.get("dir", "Unknown")  # "Buy" or "Sell"
        size = float(trade.get("sz", 0))
        price = float(trade.get("px", 0))
        time = float(trade.get("time", 0))
        closed_pnl = float(trade.get("closedPnl", 0))

        key = (coin, direction)
        trade_summary[key]["total_size"] += size
        trade_summary[key]["total_price"] += price
        trade_summary[key]["total_pnl"] += closed_pnl
        trade_summary[key]["total_time"] += time
        trade_summary[key]["count"] += 1

    # Formatting the aggregated results
    aggregated_trades = []
    for (coin, direction), data in trade_summary.items():
        avg_price = data["total_price"] / data["count"] if data["count"] > 0 else 0
        avg_pnl = data["total_pnl"] / data["count"] if data["count"] > 0 else 0
        avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
        aggregated_trades.append({
            "user": user_address,
            "coin": coin,
            "direction": direction,
            "total_size": round(data["total_size"], 2),
            "avg_price": round(avg_price, 2),
            "avg_closedPnl": round(avg_pnl, 2),
            "avg_exec_time": convert_melbourne_datetime(avg_time),
            "position_value": round(avg_price * data["total_size"], 2)
        })
    # filter by position_value
    aggregated_trades = [trade for trade in aggregated_trades if trade.get("position_value", 0) > 10000]
    # sort by exec_time
    sorted_trades = sorted(aggregated_trades, key=lambda trade: trade.get("avg_exec_time", 0), reverse=True)
    return sorted_trades

def convert_melbourne_datetime(timestamp_ms):
    # Convert to seconds
    timestamp_sec = timestamp_ms / 1000

    # Convert to datetime (UTC)
    utc_time = datetime.utcfromtimestamp(timestamp_sec).replace(tzinfo=pytz.utc)

    # Convert to Melbourne time
    melbourne_tz = pytz.timezone("Australia/Melbourne")
    melbourne_time = utc_time.astimezone(melbourne_tz)

    # Display the result
    return melbourne_time.strftime("%Y-%m-%d %H:%M:%S %Z")

def format_trade_data(trade_data):
    """
    Format aggregated trade data into an HTML table for Telegram display.
    
    :param trade_data: List of dictionaries containing aggregated trade data.
    :return: Formatted string in HTML suitable for Telegram messages.
    """
    if not trade_data:
        return "<b>No recent trades found.</b>"

    # Start HTML table
    table_str = f"Checking for new trades in the last {VP_PERIODICAL_CHECK_TIME/60} minute..."
    table_str += "<pre>\n"
    table_str += "{:<10} {:<8} {:<16} {:<15} {:<25} {:<10} ${:<12} ${:<10}\n".format(
        "Address", "Coin", "Direction", "PositionValue", "ExecTime", "TotalSize", "AvgPrice", "AvgPnL"
    )
    table_str += "-" * 120 + "\n"

    # Loop through trades and format each row
    for trade in trade_data:
        # Shorten user address (e.g., 0xf3f496c9486be5924a93d67e98298733bb47057c → 0xf3...057c)
        short_address = f"{trade['user'][:4]}...{trade['user'][-4:]}"
        url_address = f"https://hyperdash.info/trader/{trade['user']}"
        url_address = f"<a href='{url_address}'>{short_address}</a>"

        # Format the row
        table_str += "{:<20} {:<8} {:<16} ${:<15,.2f} {:<15} {:<10,.2f} ${:<12,.2f} ${:<10,.2f}\n".format(
            url_address,  # Add hyperlink to address
            trade.get("coin", ""),
            trade.get("direction", ""),
            trade.get("position_value", 0),
            trade.get("avg_exec_time", 0),
            trade.get("total_size", 0),
            trade.get("avg_price", 0),
            trade.get("avg_pnl", 0)
        )

    table_str += "</pre>"
    print(table_str)
    return table_str

async def send_to_telegram(message):
    """
    Send a formatted message to the Telegram group.
    """
    await bot.send_message(chat_id=VP_CRYPTO_GROUP_CHAT_ID, message_thread_id=VP_CRYPTO_GROUP_CHAT_TOPIC_ID, text=message)
    await bot.session.close()

async def monitor_trades():
    """
    Periodically check for new trades every 5 minutes.
    """
    # while True:
    print(f"Checking for new trades in the last {VP_PERIODICAL_CHECK_TIME/60} minute...")
    formatted_message = ""
    trades = []

    for user_address in USER_ADDRESSES:
        trade = await fetch_recent_trades(user_address) 
        if trade:
            trades += trade
        
    if len(trades) > 0:
        formatted_message = format_trade_data(trades)
        await send_to_telegram(formatted_message)
    else:
        await send_to_telegram(f"No trades found in the last {VP_PERIODICAL_CHECK_TIME/60} minute.")

        # await asyncio.sleep(VP_PERIODICAL_CHECK_TIME)  # Wait for 5 minutes before checking again

if __name__ == "__main__":
    asyncio.run(monitor_trades())
