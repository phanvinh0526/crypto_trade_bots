import logging, time, re, os, json
import requests, json
import pandas as pd
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.tl.types import PeerChat

import psycopg2
from psycopg2 import sql


# ###### DESCRIPTION ###### #
# This bot is to measure tokens performance, then enrich token_pool_info to token_pool_info_summary
# Process:
#   1.  Measure wallet tracking by counting the appearances in "wallet_tracking_info" table
#   2.  Count the appearance of the CA in GMGN group and BonkBot group
#   3.  Count number of followers on Tweeter of the token (need to extract Tweeter info of the token if not available)
#   4.  Count number of subscribers on Telegram of the token (`same as above`)
#   5.  Count number of tweet/retweet/post mention the CA on Tweeter
#   6.  Throughout the process, keep the versioning update (SCD type 2)
#-------------------------#

# ######### Variables ######### #
# ----------------------------- #
MAX_TOKEN_SCAN_PER_RUN = 200
# MAX_TOKEN_SCAN_PER_RUN = os.environ['MAX_TOKEN_SCAN_PER_RUN']
BATCH_SIZE = 30 # Maximum: 30

# Telegram Variables
# V_API_ID        = os.environ["TELE_API_ID"]
V_API_ID        = '24890651'
# V_API_HASH      = os.environ["TELE_API_HASH"]
V_API_HASH      = '7662a65de55b21a4349bf0ceb078bd67'
# V_API_PHONE     = os.environ["TELE_PHONE"]
V_API_PHONE     = '+61402329029'
TELE_SESSION_FILE_LOGIN = "tele_session_file_login_private"

TELE_GROUPS = {
    # "index_n_bonkbot_present": -1002022757177, # -100: search exactly GetHistoryRequest, while positive number is to get cached of a user
    "index_n_gmgn_present": -1002202241417
}

# TAR_FORUM_ID = os.environ['TAR_FORUM_ID']
TAR_FORUM_ID = -1002229815206
# TAR_TOPIC_ID = os.environ['TAR_TOPIC_ID']
TAR_TOPIC_ID = 12712
TAR_TROJAN_TRADE_BOT = 6511860356

# BirdEyes Variables
# BIRDEYE_API_TOKEN   = os.environ['BIRDEYE_API_TOKEN']
BIRDEYE_API_TOKEN   = "6af62e0ddb424d288693b68e3c72805e"
BIRDEYE_API_HEADER = {
    "x-chain": "solana",
    "X-API-KEY": BIRDEYE_API_TOKEN
}
BIRDEYE_API_ENDPOINT = "https://public-api.birdeye.so/"


# Connect to PostgresDb
# DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = 'postgres://u7r3q8fi3oil8d:p7c4ab7923edcd720fad4e7373c00c69924b36cd5449778bcf0e5a70268616cdd@cbec45869p4jbu.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2jp5l4pcu7iuv'


# Setup logging
logging.basicConfig(level=logging.ERROR)

# ######### Functions ######### #
# ----------------------------- #
def get_token_pool_info() -> list:
    """This function to pull out information from src table
    Args:
    """
    try:
        # Open a live connection to db
        conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor  = conn.cursor()
        start_time = time.time()
        # prepare query
        query_statement = f'''
            select tpi.network ,tpi.ca ,tpi.ticker ,tpi.token_name ,tpi.description
                ,case when tpis.market_cap is null then tpi.market_cap else tpis.market_cap end as market_cap
                ,case when tpis.liquidity_pool_value is null then tpi.liquidity_pool_value else tpis.liquidity_pool_value end as liquidity_pool_value
                ,tpis.total_holder ,tpi.gmgn_url
                ,tpis.index_n_smartwallet_bought, tpis.index_n_gmgn_present ,tpis.index_n_bonkbot_present
                ,tpis.index_n_follower_twitter ,tpis.index_n_subscriber_telegram ,tpis.index_n_twitter_search_result
                ,tpis.twitter_url ,tpis.telegram_url ,tpis.website_url ,tpi.created_at 
            from token_pool_info tpi 
            full outer join (
                select *
                from token_pool_info_summary 
                where scd_current = 1 and ctl_created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours'
            ) tpis
            on tpis.ca = tpi.ca
            where tpi.network = 'Solana'
                and tpi.created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours' -- only token created in the last 24 hours
                and (tpis.market_cap between 10000 and 100000000 or tpis.market_cap is null) and (tpis.liquidity_pool_value >= 5000 or tpis.liquidity_pool_value is null)
            order by tpi.created_at desc
            limit {MAX_TOKEN_SCAN_PER_RUN}
        '''
        # exec sql query
        cursor.execute(query_statement)

        # fetch all rows, and convert to a list of dictionary type
        cols = [desc[0] for desc in cursor.description] # get col name from cursor description
        results = [dict(zip(cols, row)) for row in cursor.fetchall()]
        # print(f"Raw Results: {results}")

        # Get Twitter and Telegram url
        resp = []
        for batch in split_batches(results, BATCH_SIZE):
            data = crawl_x_tele_from_gmgn(batch)
            if data:
                resp.extend(data)

        # Elapse time & return
        elapsed_time = round(time.time() - start_time, 2)
        print(f"*** 1. Get `token_pool_info` and crawling data from GMGN | Elapsed time: {elapsed_time}sec")
        # print(f'Result: {results}')
        return resp

    except (psycopg2.Error()) as error:
        print(f"--- ERROR: while querying data from [token_pool_info] table: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def crawl_x_tele_from_gmgn(batch) -> dict:
    """The function to crawl tele_url, website, x_url and token info
    from DexScreener API
    Args:
        batch (_type_): a subset of tokens
    Returns:
        dict: token information including social links
    """
    try:
        # Variables
        API_URL = 'https://api.dexscreener.com/latest/dex/tokens'
        token_addresses = ','.join([i['ca'] for i in batch])

        # Fetch the page content
        response = requests.get(f'{API_URL}/{token_addresses}')
        response.raise_for_status()  # Ensure we notice bad responses
        data = json.loads(response.text)

        # Extracting the details for the raydium dexId
        tokens = []
        for pair in data['pairs']:
            if pair['dexId'] == 'raydium' and pair['liquidity']['usd'] >= 10000:
                obj = {}
                obj['ca'] = str(pair['baseToken']['address']).lower()
                obj['liquidity_pool_value'] = pair['liquidity']['usd']
                obj['market_cap'] = pair['fdv']
                if 'info' in pair:
                    obj['website_url'] = pair['info']['websites'][0]['url'] if len(pair['info']['websites']) != 0 else None
                    obj['twitter_url'] = next((social['url'] for social in pair['info']['socials'] if social['type'] == 'twitter'), None)
                    obj['telegram_url'] = next((social['url'] for social in pair['info']['socials'] if social['type'] == 'telegram'), None)
                tokens.append(obj)

        # for idx, i in enumerate(tokens[0:]):
        #     for jid, j in enumerate(tokens[i:]):
        #         if i['ca'] == j['ca'] and i['liquidity_pool_value'] < j['liquidity_pool_value']:
        #             tokens[idx] = j
        #             tokens.remove(jid)
        seen = set()
        tokens = [x for x in tokens if x['ca'] not in seen and not seen.add(x['ca'])]

        # Update response
        for idx, val in enumerate(batch):
            result = next((item for item in tokens if item['ca'] == val['ca']), None)
            if result:
                batch[idx].update(result)

        return batch

    except (Exception) as e:
        print(f"--- ERROR: Crawl x and tele func returned an error message: {e}")
        return None
    

def is_valid_url(url):
    if not url:
        return False
    # Basic URL validation
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if re.match(regex, url) is None:
        return False
    return True


def crawl_telegram_subscriber(url):
    """The function is to crawl telegram web to search for subscribers
    Note that: the subscribers is different to participants / followers of the channel
    Args:
        url (_type_): telegram url
    """
    try:
        if is_valid_url(url):
            # Fetch the content of the URL
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Crawl_keyword function | Failed to fetch the URL: {url}")
                return None

            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            body_text = soup.get_text().lower()
            # Search for number of subscribers
            match = re.search(r'(\d[\d\s]*)\s+[subscribers,members]', body_text)

            if match:
                subscribers = int(match.group(1).replace(" ",""))
                if subscribers:
                    return subscribers
        return None
    
    except (Exception) as error:
        print(f"--- ERROR: crawl_telegram_subscriber function error occured with message: {error}")
        return None
    

def get_telegram_subscriber(token_info) -> dict:
    start_time = time.time()
    for idx, val in enumerate(token_info):
        if val['telegram_url']:
            ctn = crawl_telegram_subscriber(val['telegram_url'])
            token_info[idx]['index_n_subscriber_telegram'] = ctn
        else:
            token_info[idx]['index_n_subscriber_telegram'] = 0
    
    # Elapse time & return
    elapsed_time = round(time.time() - start_time, 2)
    print(f"*** 4. Get telegram subscriber | Elapsed time: {elapsed_time}sec")
    return token_info


def count_appearances_ca_wallettracking(token_info) -> list:
    """This function to count the appereances of the CA in `wallet_tracking_info`
    Args:
        token_info: token info object
    """
    try:
        # Open a live connection to db
        conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor  = conn.cursor()
        start_time = time.time()
        # prepare query
        lst_ca = [item['ca'] for item in token_info]
        query_statement = sql.SQL('''
            select ticker_ca, count(distinct wallet_address) as index_n_smartwallet_bought
            from wallet_tracking_info
            where ticker_ca in ({})
            group by ticker_ca 
        ''').format(
            sql.SQL(', ').join(map(sql.Literal, lst_ca))
        )

        # exec sql query
        # print(f"Query: {query_statement.as_string(cursor)}")
        cursor.execute(query_statement)

        # fetch all rows, and convert to a list of dictionary type
        cols = [desc[0] for desc in cursor.description] # get col name from cursor description
        results = [dict(zip(cols, row)) for row in cursor.fetchall()]

        # Update token_info
        for idx, val in enumerate(token_info):
            # if ticker in the results list
            for r in results:
                if val['ca'] == r['ticker_ca']:
                    token_info[idx]['index_n_smartwallet_bought'] = r['index_n_smartwallet_bought']
            # if ticker is not in the results
            if val['ca'] in lst_ca and val['index_n_smartwallet_bought'] is None:
                token_info[idx]['index_n_smartwallet_bought'] = 0


        # Elapse time & return
        elapsed_time = round(time.time() - start_time, 2)
        print(f"*** 2. Count appearances of CA in WalletTracking table | Elapsed time: {elapsed_time}sec")
        return token_info

    except (Exception) as error:
        print(f"--- ERROR: while querying data from [wallet_tracking_info] table: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def count_appearances_ca_gmgn_bonkbot(token_info: list) -> list:
    try:
        start_time = time.time()
        if len(token_info) == 0:
            print("No data received from the table!.")
            return None
        # Create the client and connect
        client = TelegramClient(TELE_SESSION_FILE_LOGIN, V_API_ID, V_API_HASH)
        # Connect to tele server. For the first time, it promps to ask for Login code, then save it into TELE_SESSION_FILE_LOGIN
        await client.start(phone = V_API_PHONE)
            
        # Count appearance of each ca in each group
        for key, val in TELE_GROUPS.items():
            group = await client.get_input_entity(val)

            # for each ca, count appearances
            for idx, row in enumerate(token_info):
                ctn_present = 0
                ca = row["ca"]
                # iterate through messages in the group
                async for message in client.iter_messages(entity=group, search=ca, limit=1500, wait_time=0):
                    ctn_present += 1
                # update count to the result list
                token_info[idx][key] = ctn_present

        # Elapse time & return
        elapsed_time = round(time.time() - start_time, 2)
        print(f"*** 3. Count apperances of CA in {list(TELE_GROUPS.keys())} Telegram channels | Elapsed time: {elapsed_time}sec")
        return token_info

    except (Exception) as error:
        print(f"--- ERROR: in TelegramClient connection: {error}")
        return None

    finally:
        if client:
            await client.disconnect()

def clean_special_characters(value):
    # Remove or escape special characters
    if isinstance(value, str):
        # Example: Removing single quotes and other special characters
        value = re.sub(r"[\'\"\\]", "", value)
    return str(value)


def split_batches(lst, batch_size):
    return [lst[i:i + batch_size] for i in range(0, len(lst), batch_size)]


def update_token_pool_summary_tbl(token_info):
    """The function is to update the token_pool_summary table
    Args:
        token_info (list): _description_
    """
    try:
        # Open a live connection to db
        start_time = time.time()
        conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor  = conn.cursor()

        # Prepare the insert statement dynamically
        queries = []
        cols = [f"p_{item}" for item in list(token_info[0].keys())]

        # Apply SCD Type 2 for every single token, and insert into token_pool_summary table
        for row in token_info:
            # Clean data input
            values = [clean_special_characters(val) for val in row.values()]
            values = list(map(":=".join, zip(cols, values)))
            values = (str(values).replace(":=", ":='").replace(", '", ", ").replace("['", '').replace(']', '')).replace('"', '')

            # Prepare insert statement
            scd2_statement = ("call update_scd_to_token_pool_info_summary({parameters})").format(
                parameters = values
            )
            queries.append(scd2_statement)

        # Execute
        for batch_queries in split_batches(queries, BATCH_SIZE):
            try:
                query = "; ".join(batch_queries)
                # print(f'Query: {query}')
                cursor.execute(query)
                conn.commit()

            except (psycopg2.Error) as e:
                print(f"--- ERROR: Function `update_token_pool_summary_tbl` | Error message: {e}")
                # print(queries)
                conn.rollback() # Rollback the current transaction to skip the faulty row

        print(f"{len(token_info)} records have been added to `token_pool_info_summary`.")

        # Elapse time & return
        elapsed_time = round(time.time() - start_time, 2)
        print(f"*** 5. Update `token_pool_summary` table | Elapsed time: {elapsed_time}sec")

    except (Exception) as error:
        print(f"--- ERROR: Update `token_pool_summary_tbl` error occured with message {error}") 
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def read_data_from_db():
    try:
        # Connection
        conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor  = conn.cursor()
        # Read data
        query = """
                select report_date, ca, ticker, token_name, market_cap, 
                    index_n_subscriber_telegram, idx_total_inc_per, gmgn_url, twitter_url, 
                    token_created_at, ctl_created_at, index_n_gmgn_present, index_n_smartwallet_bought
                from v_search_gems_recent_launched limit 2;
            ;
        """
        cursor.execute(query)
        cols = [desc[0] for desc in cursor.description]
        results = [dict(zip(cols, row)) for row in cursor.fetchall()]

        # Reformat the result for Tele msg
        response = []
        if results:
            for result in results:
                # Format the message
                message = (
                    f"**Top 1st Recent Launched Token by Liquidity Pool Spike:**\n\n"
                    f"**Logarithm Index:** {result['idx_total_inc_per']}\n"
                    f"**Ticker:** {result['ticker']}\n"
                    f"**Token Name:** {result['token_name']}\n"
                    f"**Market Cap:** {result['market_cap']}\n"
                    f"**GMGN Index:** {result['index_n_gmgn_present']}\n"
                    f"**Smart Wallet Transactions Index:** {result['index_n_smartwallet_bought']}\n"
                    f"**Telegram Subscriber:** {result['index_n_subscriber_telegram']}\n"
                    f"**Twitter URL:** {result['twitter_url']}\n"
                    f"**GMGN URL:** {result['gmgn_url']}\n"
                    f"**Token Created At:** {result['token_created_at']}\n"
                    f"**Last time retrieve info:** {result['ctl_created_at']}\n"
                )
                response.append({'ca':result['ca'], 'msg':message})

        return response

    except (Exception) as error:
        print(f"--- ERROR: `read_data_from_db` error occured with message {error}") 
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def save_df_to_csv(df, file_path):
    try:
         df.to_csv(file_path, index=False)
    except Exception as e:
        print(f"--- ERROR: in saving DataFrame to CSV: {e}")


async def send_file_to_tele(file_path, forum_id, topic_id):
    """Send a file to a Telegram group chat"""
    try:
        # Create the client and connect
        client = TelegramClient(TELE_SESSION_FILE_LOGIN, V_API_ID, V_API_HASH)
        await client.connect()

        # Send file
        await client.send_file(entity=TAR_FORUM_ID, file=file_path, caption="Token Summary | Generated every hour")
        print("** File send successfully.")

    except Exception as e:
        print(f"--- ERROR: sending csv file to Telegram: {e}")
    finally:
        await client.disconnect()


async def send_msg_to_tele(msg_ca, forum_id, topic_id):
    """Send a text message to a Telegram group chat"""
    try:
        # Create the client and connect
        client = TelegramClient(TELE_SESSION_FILE_LOGIN, V_API_ID, V_API_HASH)
        await client.connect()

        # Send msg to Gem Searching group
        await client.send_message(entity=TAR_FORUM_ID, message=msg_ca['msg'])

        # Send ca to Trojen trading bot
        # await client.send_message(entity=TAR_TROJAN_TRADE_BOT, message=msg_ca['ca'])

        print("** Msg has been sent successfully.")

    except Exception as e:
        print(f"--- ERROR: sending csv file to Telegram: {e}")
    finally:
        await client.disconnect()


async def send_view_summary_to_telegram():
    """This function is to pull out data from the view, and upload csv file to Telegram group
    """
    # Variables
    start_time = time.time()

    # Extract data from postgresql
    resp = read_data_from_db()
    if len(resp) >= 1:
        for r in resp:
            await send_msg_to_tele({'msg':r['msg'], 'ca':r['ca']}, TAR_FORUM_ID, TAR_TOPIC_ID)

    else:
        print("--- ERROR: `send_view_summary_to_telegram` | No data to upload.")
    
    elapsed_time = round(time.time() - start_time, 2)
    print(f"*** 7. Message has been sent to Telegram group | Elapsed time: {elapsed_time}sec")

def store_results_to_db():
    """The function to save restuls from reporting views to a table
    """
    try:
        # Connection
        start_time = time.time()
        conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor  = conn.cursor()
        # Read data
        query = '''
            call insert_report_data_from_view('tpis_search_gems_recent_launched', 'tbl_reports_records');
            call insert_report_data_from_view('tpis_search_gems_low_mc', 'tbl_reports_records');
        '''
        cursor.execute(query)
        conn.commit()

        # Elapse time & return
        elapsed_time = round(time.time() - start_time, 2)
        print(f"*** 6. `store_results_to_db` complete without an error | Elapsed time: {elapsed_time}sec")

    except (Exception) as error:
        print(f"--- ERROR: `Store Proc: insert_report_data_from_view` error occured with message {error}") 
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ######### Main Func ######### #
# ----------------------------- #
async def main_func() -> None:
    """The main function which will execute every 1 hour to collect information for each token in the table"""
    # Local variables

    # Run
    try:
        # Run
        main_start_time = time.time()
        print("-------------------------------------------------------------")
        print(f"Measure token perform function started !!! | MAX_TOKEN_SCAN_PER_RUN = {MAX_TOKEN_SCAN_PER_RUN}")
        print(f"Start time (utc): {datetime.now(timezone.utc)}")
        
        # Retrieve a list of tokens to monitor (no more than 1000 tokens)
        token_pool = get_token_pool_info()

        # Count the CA presents in wallet_tracking_info table
        token_pool = count_appearances_ca_wallettracking(token_pool)

        # Count the CA presents as a result of GMGN and BonkBot channel
        token_pool = await count_appearances_ca_gmgn_bonkbot(token_pool)

        # Count number of followers on X
        # TODO

        # Count number of subscribers on Telegram
        token_pool = get_telegram_subscriber(token_pool)

        # Count number of top results on Twitter (limit to 1000 results max)
        # TODO

        # Update 'token_pool" to the db table
        update_token_pool_summary_tbl(token_pool)

        # Store the report results into the result table
        store_results_to_db()

        # Send a summary to Tele group
        await send_view_summary_to_telegram()

        # Logging
        elapsed_time = round(time.time() - main_start_time, 2)
        print("Measure token perform function finish sucessfully !!!")
        print(f"Finish time (utc): {datetime.now(timezone.utc)}")
        print(f"***** Total elapsed time for a run: {elapsed_time}sec. *****")
        print("-------------------------------------------------------------")

    except (Exception) as error:
        print(f"--- ERROR: in Main function: {error}")
        print("Process stopped!!!")


# if __name__ == "__main__":
#     asyncio.run(main())


# #### Appendix #### #
