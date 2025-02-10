import schedule
import asyncio
import time, os
from telethon import TelegramClient
from create_tele_session_file import TELE_SESSION_FILE_LOGIN, TELE_SESSION_FILE_PATH, V_API_ID, V_API_HASH
from create_tele_session_file import download_binary_file
from index_measure_token_performance import main_func


# Flag to indicate if a job is currently running
job_running = False


# ##### Functions ##### #
# --------------------- #
async def check_tele_conn_auth():
    # Connecting
    try:
        client = TelegramClient(TELE_SESSION_FILE_LOGIN, V_API_ID, V_API_HASH)
        await client.connect()
        
        if client.is_connected():
            print("TelegramClient connected!")
        else:
            print("TelegramClient not connected!")
            return False
        
        if await client.is_user_authorized():
            print("Client is authorized")
        else:
            print("Client is not authorized. Please log in.")
            return False

        await client.disconnect()
        return True

    except (Exception) as e:
        print(f"Cannot create connection to TelegramClient with error message: {e}")
        return False


async def measure_token_performance():
    try:
        # Download session file from PostgreSQL table
        filename = f"{TELE_SESSION_FILE_LOGIN}.session"
        filepath = os.path.join(TELE_SESSION_FILE_PATH, filename)
        if not os.path.exists(filepath):
            # download the tele private session file
            download_binary_file(filename)
            time.sleep(5)

        # Test the TelegramClient connection
        if await check_tele_conn_auth():
            await main_func()

    except (Exception) as e:
        print(f"*** Scheduler returns an error message: {e}")


async def execute_job():
    await measure_token_performance()


def run_async_job():
    global job_running
    if not job_running:
        job_running = True
        asyncio.run(execute_job())
        job_running = False


# Schedule the job every 45 minutes
schedule.every(20).minutes.do(run_async_job)

# Keep the script running to execute scheduled jobs
if __name__ == '__main__':
    while True:
        schedule.run_pending()
        time.sleep(10)

# if __name__ == "__main__":
#     asyncio.run(job_measure_token_performance())