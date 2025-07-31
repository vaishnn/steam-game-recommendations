# %%
import pymysql
from pymysql import cursors
import os
from dotenv import load_dotenv

def connect_to_mariadb():
    load_dotenv()

    DB_HOST = str(os.getenv('DB_HOST'))
    DB_USER = str(os.getenv('DB_USER'))
    DB_PASSWORD = str(os.getenv('DB_PASSWORD'))
    DB_NAME = str(os.getenv('DB_NAME'))
    DB_PORT = str(os.getenv('DB_PORT'))

    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT]):
        raise ValueError("Missing environment variables")
        return

    connection = None
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=int(DB_PORT),
            cursorclass=cursors.DictCursor
        )
        print("Successfully connected to the server")

        with connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS games (

                )

                )
                """)
    except pymysql.Error as e:
        print(f"Failed to connect to MariaDB: {e}")
    return connection

connect_to_mariadb()

# %%
