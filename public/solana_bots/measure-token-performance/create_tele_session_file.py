import asyncio
import logging, time, re, os, json
import requests, json
from telethon import TelegramClient
import psycopg2

# Telegram Variables
# V_API_ID        = os.environ["TELE_API_ID"]
V_API_ID        = '24890651'
# V_API_HASH      = os.environ["TELE_API_HASH"]
V_API_HASH      = '7662a65de55b21a4349bf0ceb078bd67'
# V_API_PHONE     = os.environ["TELE_PHONE"]
V_API_PHONE     = '+61402329029'
TELE_SESSION_FILE_LOGIN = "tele_session_file_login_private"
TELE_SESSION_FILE_PATH  = f"./"

# Connect to PostgresDb
# DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = 'postgres://u7r3q8fi3oil8d:p7c4ab7923edcd720fad4e7373c00c69924b36cd5449778bcf0e5a70268616cdd@cbec45869p4jbu.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2jp5l4pcu7iuv'


# Create a new TelegramClient instance with a unique session
client = TelegramClient(TELE_SESSION_FILE_LOGIN, V_API_ID, V_API_HASH)

async def setup_tele_conn():
    await client.start(phone = V_API_PHONE)
    print("Client connected | Session file generated.")


# Insert session file to database
def upload_binary_file(file_path):
    """Insert a binary file into PostgreSQL table
    Args:
        file_path: <desc>
    """
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor = conn.cursor()

        # Read the binary file
        with open(file_path, 'rb') as file:
            file_content = file.read()

        # Get the filename
        filename = os.path.basename(file_path)

        # Insert the binary file into the database
        insert_query = """
            INSERT INTO tele_session_binary_files (file_name, content)
            VALUES (%s, %s)
            ON CONFLICT (file_name) 
            DO UPDATE SET content = %s;
        """
        cursor.execute(insert_query, (filename, file_content, file_content))

        # Commit the transaction
        conn.commit()
        print(f"File '{filename}' uploaded successfully.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error uploading file: {error}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def download_binary_file(filename):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor = conn.cursor()

        # Retrieve the binary file from the database
        select_query = f'''
            SELECT file_name, content
            FROM tele_session_binary_files
            WHERE file_name = '{filename}';
        '''
        cursor.execute(select_query)
        result = cursor.fetchone()

        if result is None:
            print(f"No file found with filename: {filename}.")
            return

        filename, file_content = result

        # Create the output path if it does not exist
        if not os.path.exists(TELE_SESSION_FILE_PATH):
            os.makedirs(TELE_SESSION_FILE_PATH)

        # Write the binary file to the output path
        output_file_path = os.path.join(TELE_SESSION_FILE_PATH, filename)
        with open(output_file_path, 'wb') as file:
            file.write(file_content)

        print(f"*** File '{filename}' downloaded and saved to '{output_file_path}'.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error uploading file: {error}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Main func
if __name__ == "__main__":
    # Setup tele session file
    asyncio.run(setup_tele_conn())

    # Wait 5 seconds to complete the process
    time.sleep(5)

    # Upload session file to PostgreSQL table
    file_path = f"{TELE_SESSION_FILE_PATH}{TELE_SESSION_FILE_LOGIN}.session"
    upload_binary_file(file_path)
    time.sleep(3)

    # Download session file from PostgreSQL table
    output_path = f"{TELE_SESSION_FILE_PATH}/bk/"
    download_binary_file(output_path)
    time.sleep(3)


# ##### APPENDIX ##### #
# CREATE TABLE tele_session_binary_files (
#     id SERIAL PRIMARY KEY,
#     filename TEXT,
#     content BYTEA
# );
