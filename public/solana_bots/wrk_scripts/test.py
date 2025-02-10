import logging, time, re, os, json
import requests, json
import pandas as pd
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.tl.types import PeerChat

import psycopg2
from psycopg2 import sql

import re

MAX_TOKEN_SCAN_PER_RUN = 9
BATCH_SIZE = 5
DATABASE_URL = 'postgres://u7r3q8fi3oil8d:p7c4ab7923edcd720fad4e7373c00c69924b36cd5449778bcf0e5a70268616cdd@cbec45869p4jbu.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2jp5l4pcu7iuv'


    # Connection
conn    = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor  = conn.cursor()
# Read data
query = """
    SELECT ca, ticker, token_name, market_cap, market_cap_inc_per, liquidity_pool_value, 
        liquidity_pool_value_inc_per, index_n_gmgn_present, index_n_gmgn_present_inc_per, index_n_smartwallet_txn, 
        index_n_subscriber_telegram, index_n_subscriber_telegram_inc_per,
        total_holder, total_holder_inc_per, gmgn_url, token_created_at, ctl_created_at
    FROM tpis_search_gems_recent_launched
    ORDER BY liquidity_pool_value_inc_per DESC
    LIMIT 2;
    ;
"""
cursor.execute(query)
cols = [desc[0] for desc in cursor.description]
results = [dict(zip(cols, row)) for row in cursor.fetchall()]

# Reformat the result for Tele msg
message = ""
ca = None
if results:
    for result in results:
        # Format the message
        message = (
            f"**Top 1st Recent Launched Token by Liquidity Pool Spike:**\n\n"
            f"**Ticker:** {result['ticker']}\n"
            f"**Token Name:** {result['token_name']}\n"
            f"**Market Cap:** {result['market_cap']}\n"
            f"**Market Cap Increase (%):** {result['market_cap_inc_per']}\n"
            f"**Liquidity Pool Value:** {result['liquidity_pool_value']}\n"
            f"**Liquidity Pool Value Increase (%):** {result['liquidity_pool_value_inc_per']}\n"
            f"**GMGN Index:** {result['index_n_gmgn_present']}\n"
            f"**GMGN Index Increase (%):** {result['index_n_gmgn_present_inc_per']}\n"
            f"**Smart Wallet Transactions Index:** {result['index_n_smartwallet_txn']}\n"
            f"**Telegram Subscriber:** {result['index_n_subscriber_telegram']}\n"
            f"**Telegram Subscriber Increase (%):** {result['index_n_subscriber_telegram_inc_per']}\n"
            f"**Total Holders:** {result['total_holder']}\n"
            f"**Total Holders Increase (%):** {result['total_holder_inc_per']}\n"
            f"**GMGN URL:** {result['gmgn_url']}\n"
            f"**Token Created At:** {result['token_created_at']}\n"
            f"**Last time retrieve info:** {result['ctl_created_at']}\n"
        )

        print(message)
else:
    message = "No data found."