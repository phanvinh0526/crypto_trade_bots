"Detect  New Pools Created on Solana Raydium DEX"

#MAnually see transactions of new pairs GThUX1Atko4tqhN2NaiTazWSeFWMuiUvfFnyJyUghFMJ under spl transfer section

from time import sleep
from datetime import datetime
import logging
import pytz, requests, json, re

import asyncio
from typing import List, AsyncIterator, Tuple, Iterator
from asyncstdlib import enumerate

from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsFilterMentions

from solana.rpc.websocket_api import connect
from solana.rpc.commitment import Finalized
from solana.rpc.api import Client
from solana.exceptions import SolanaRpcException
from websockets.exceptions import ConnectionClosedError, ProtocolError

# Type hinting imports
from solana.rpc.commitment import Commitment
from solana.rpc.websocket_api import SolanaWsClientProtocol
from solders.rpc.responses import RpcLogsResponse, SubscriptionResult, LogsNotification, GetTransactionResp
from solders.signature import Signature
from solders.transaction_status import UiPartiallyDecodedInstruction, ParsedInstruction


# Raydium Liquidity Pool V4
RaydiumLPV4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
URI = "https://greatest-serene-frog.solana-mainnet.quiknode.pro/d9956a657fc3ca286b0ee009465a5b704753fb95/"  # "https://api.devnet.solana.com" | "https://api.mainnet-beta.solana.com"
WSS = "wss://greatest-serene-frog.solana-mainnet.quiknode.pro/d9956a657fc3ca286b0ee009465a5b704753fb95/"  # "wss://api.devnet.solana.com" | "wss://api.mainnet-beta.solana.com"
solana_client = Client(URI)


# BirdEye APIs
BIRDEYE_API_TOKEN  = "6af62e0ddb424d288693b68e3c72805e"
headers = {
    "x-chain": "solana",
    "X-API-KEY": BIRDEYE_API_TOKEN
}
birdeye_endpoint = "https://public-api.birdeye.so/"


# Telegram interactions
TELE_BOT_TOKEN      = "6353515472:AAFA-zXzKnZcm66IKEmsGvjJtX4Iq0-tj1g"
TAR_FORUM_ID        = -1002229815206
TAR_TOPIC_ID        = 5795
TELE_API_ENDPOINT   = f'https://api.telegram.org/bot{TELE_BOT_TOKEN}/sendMessage'



# Raydium function call name, look at raydium-amm/program/src/instruction.rs
log_instruction = "initialize2"
seen_signatures = set()


# Init logging
logging.basicConfig(filename='app.log', filemode='a', level=logging.DEBUG)
# Writes responses from socket to messages.json
# Writes responses from http req to  transactions.json

async def main():
    """The client as an infinite asynchronous iterator:"""
    async for websocket in connect(WSS):
        try:
            print(f"Started... at {datetime.now(pytz.timezone('Australia/Melbourne'))}")
            subscription_id = await subscribe_to_logs(
                websocket,
                RpcTransactionLogsFilterMentions(RaydiumLPV4),
                Finalized
            )
            # Change level debugging to INFO
            logging.getLogger().setLevel(logging.INFO)  # Logging
            async for i, signature in enumerate(process_messages(websocket, log_instruction)):  # type: ignore
                logging.info(f"{i=}")  # Logging
                try:
                    get_tokens(signature, RaydiumLPV4)
                except SolanaRpcException as err:
                    # Omitting httpx.HTTPStatusError: Client error '429 Too Many Requests'
                    # Sleep 5 sec, and try connect again
                    # Start logging
                    logging.exception(err)
                    logging.info("sleep for 5 seconds and try again")
                    # End logging
                    sleep(5)
                    continue
        except (ProtocolError, ConnectionClosedError) as err:
            # Restart socket connection if ProtocolError: invalid status code
            logging.exception(err)  # Logging
            print(f"Danger! Danger!", err)
            continue
        except KeyboardInterrupt:
            if websocket:
                await websocket.logs_unsubscribe(subscription_id)


async def subscribe_to_logs(websocket: SolanaWsClientProtocol, 
                            mentions: RpcTransactionLogsFilterMentions,
                            commitment: Commitment) -> int:
    await websocket.logs_subscribe(
        filter_=mentions,
        commitment=commitment
    )
    first_resp = await websocket.recv()
    return get_subscription_id(first_resp)  # type: ignore


def get_subscription_id(response: SubscriptionResult) -> int:
    return response[0].result


async def process_messages(websocket: SolanaWsClientProtocol,
                           instruction: str) -> AsyncIterator[Signature]:
    """Async generator, main websocket's loop"""
    async for idx, msg in enumerate(websocket):
        value = get_msg_value(msg)
        if not idx % 100:
            pass
            # print(f"{idx=}")
        for log in value.logs:
            if instruction not in log:
                continue
            # Start logging
            logging.info(value.signature)
            logging.info(log)
            # Logging to messages.json
            with open("messages.json", 'a', encoding='utf-8') as raw_messages:  
                raw_messages.write(f"signature: {value.signature} \n")
                raw_messages.write(msg[0].to_json())
                raw_messages.write("\n ########## \n")
            # End logging
            yield value.signature


def get_msg_value(msg: List[LogsNotification]) -> RpcLogsResponse:
    return msg[0].result.value


def get_tokens(signature: Signature, RaydiumLPV4: Pubkey) -> None:
    """httpx.HTTPStatusError: Client error '429 Too Many Requests' 
    for url 'https://api.mainnet-beta.solana.com'
    For more information check: https://httpstatuses.com/429

    """
    # if signature not in seen_signatures:
    #     seen_signatures.add(signature)
    transaction = solana_client.get_transaction(
        signature,
        encoding="jsonParsed",
        max_supported_transaction_version=0
    )
    # Start logging to transactions.json
    with open("transactions.json", 'a', encoding='utf-8') as raw_transactions:
        raw_transactions.write(f"signature: {signature}\n")
        raw_transactions.write(transaction.to_json())        
        raw_transactions.write("\n ########## \n")
    # End logging
    instructions = get_instructions(transaction)
    filtred_instuctions = instructions_with_program_id(instructions, RaydiumLPV4) # search for new token listed on Raydium program
    logging.info(filtred_instuctions)
    for instruction in filtred_instuctions:
        tokens = get_tokens_info(instruction)
        print_table(tokens)
        # TODO: check if the token will not a rug fishing (https://api.rugcheck.xyz/swagger/index.html)



def get_instructions(
    transaction: GetTransactionResp
) -> List[UiPartiallyDecodedInstruction | ParsedInstruction]:
    instructions = transaction \
                   .value \
                   .transaction \
                   .transaction \
                   .message \
                   .instructions
    return instructions


def instructions_with_program_id(
    instructions: List[UiPartiallyDecodedInstruction | ParsedInstruction],
    program_id: str
) -> Iterator[UiPartiallyDecodedInstruction | ParsedInstruction]:
    return (instruction for instruction in instructions
            if instruction.program_id == program_id)


def get_tokens_info(
    instruction: UiPartiallyDecodedInstruction | ParsedInstruction
) -> Tuple[Pubkey, Pubkey, Pubkey]:
    accounts = instruction.accounts
    Pair = accounts[4]
    Token0 = accounts[8]
    Token1 = accounts[9]
    # Start logging
    logging.info("find LP !!!")
    logging.info(f"\n Token0: {Token0}, \n Token1: {Token1}, \n Pair: {Pair}")
    # End logging
    return (Token0, Token1, Pair)


def get_melbourne_time():
    # Define the Melbourne time zone
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    melbourne_time = datetime.now(melbourne_tz)
    return f"(Melbourne, AU): {melbourne_time.strftime('%Y-%m-%d %H:%M:%S')}"


def check_attribute_available(data: dict):
    lst_att = ["symbol","name","liquidity","realMc","holder","uniqueWallet30m","trade30m","buy30m","numberMarkets","extensions"]
    for att in lst_att:
        if(att not in data.keys()):
            return False
    return True


def get_token_overview(ca: str) -> dict:
    sleep(2)
    url = birdeye_endpoint + "defi/token_overview" + "?" + f"address={ca}"
    res = requests.get(url=url, headers=headers)
    res = json.loads(res.text)

    data = {}
    if(res["data"] == {}):
        return {}
    if(check_attribute_available(res["data"])):
        data["sticker"] = res["data"]["symbol"]
        data["sticker_full_name"] = res["data"]["name"]
        data["liquidity"] = format(round(res["data"]["liquidity"], 2), ',') if res["data"]["liquidity"] is not None else 0
        data["market_cap"] = format(round(res["data"]["realMc"]), ',') if res["data"]["realMc"] is not None else 0
        data["total_holder"] = format(res["data"]["holder"], ',') if res["data"]["holder"] is not None else 0
        data["unique_wallet_last_30m"] = format(res["data"]["uniqueWallet30m"], ',') if res["data"]["uniqueWallet30m"] is not None else 0
        data["num_trade_last_30m"] = res["data"]["trade30m"]
        data["num_buy_last_30m"] = res["data"]["buy30m"]
        data["num_markets"] = res["data"]["numberMarkets"]
        data["extensions"] = str(res["data"]["extensions"])
    return data


def send_msg_to_telegram(message: str) -> None:
    payload = {
        'chat_id': TAR_FORUM_ID,
        'message_thread_id': TAR_TOPIC_ID,
        'text': message
    }
    response = requests.post(url=TELE_API_ENDPOINT, data=payload)
    # Check the response
    if response.status_code == 200:
        print('Message sent successfully!')
    else:
        print('Failed to send message:', response.text)


def print_table(tokens: Tuple[Pubkey, Pubkey, Pubkey]) -> None:
    # Get token information
    CA = ''
    if(str(tokens[0]) != 'So11111111111111111111111111111111111111112'):
        CA = tokens[0]
    elif(str(tokens[1]) != 'So11111111111111111111111111111111111111112'):
        CA = tokens[1]
    else:
        return
    token_data = get_token_overview(CA)
    # Print table data
    if(token_data != {}):
        data = [
            {'Column': 'Contract Address', 'Value': CA},  # Token0
            {'Column': 'LP Pair', 'Value': tokens[2]},  # LP Pair
            {'Column': 'Detected At', 'Value': get_melbourne_time()}, # time new token detected
            {'Column': 'Sticker / Symbol', 'Value': token_data['sticker']}, # 
            {'Column': 'Sticker Name', 'Value': token_data['sticker_full_name']}, # 
            {'Column': 'Liquidity', 'Value': token_data['liquidity']}, # 
            {'Column': 'Market Cap', 'Value': token_data['market_cap']}, # 
            {'Column': 'Total Holders', 'Value': token_data['total_holder']}, # 
            {'Column': 'Unique Wallets last 30m', 'Value': token_data['unique_wallet_last_30m']}, # 
            {'Column': 'Unique Trade last 30m', 'Value': token_data['num_trade_last_30m']}, # 
            {'Column': 'Number of Buy last 30m', 'Value': token_data['num_buy_last_30m']}, # 
            {'Column': 'Number of Markets deployed', 'Value': token_data['num_markets']}, # 
            {'Column': 'Extensions', 'Value': token_data['extensions']}
        ]
    else:
        data = [
            {'Column': 'Contract Address', 'Value': CA},  # Token0
            {'Column': 'LP Pair', 'Value': tokens[2]},  # LP Pair
            {'Column': 'Detected At', 'Value': get_melbourne_time()} # time new token detected
        ]
    rep_str = ""
    rep_str = "\n==== NEW POOL DETECTED ===="
    # header = ["Column", "Value"]
    # rep_str += "│".join(f" {col.ljust(15)} " for col in header) + '\n'
    # rep_str += "|".rjust(18) + '\n'
    for row in data:
        # rep_str += "│".join(f" {str(row[col]).ljust(15)} " for col in header) + '\n'
        rep_str += '\n' + str(row['Column']) + ': ' + str(row['Value']) + '\n'

    rep_str += f"\nhttps://gmgn.ai/sol/token/{CA}"
    print(rep_str)
    # Send message to Telegram via API request
    send_msg_to_telegram(rep_str)


if __name__ == "__main__":
    RaydiumLPV4 = Pubkey.from_string(RaydiumLPV4)
    asyncio.run(main())