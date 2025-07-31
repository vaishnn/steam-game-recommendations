# %% Cell 1
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import yaml

with open("end_points.yaml", "r") as file:
    endpoints = yaml.safe_load(file)

# --- Replace with your AWS RDS credentials ---
db_host = endpoints["aws"]["end_point"] # The endpoint URL from the AWS console
db_name = endpoints["aws"]["db_name"] # The DB name you set during creation
db_user = endpoints["aws"]["db_user"]
db_password = endpoints["aws"]["db_password"]
# ---------------------------------------------
#

conn = None # Initialize connection to None
try:
    # Establish the connection
    conn = mysql.connector.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )

    if conn.is_connected():
        print("✅ Connection to AWS RDS MariaDB successful!")

        # Use a cursor to execute commands
        with conn.cursor() as cur:
            # Example: Create a table for Steam games (run this once)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS steam_games (
                    app_id INT PRIMARY KEY,
                    name VARCHAR(255),
                    last_updated TIMESTAMP
                );
            """)
            print("Table 'steam_games' is ready.")

            # Example: Insert or update data retrieved from the Steam API
            # This would be inside your loop that processes API responses
            game_data = (1091500, 'Cyberpunk 2077', datetime.now()) # Example data

            # This command will INSERT a new row. If a row with the same app_id
            # already exists, it will UPDATE the name and last_updated fields.
            insert_query = """
                INSERT INTO steam_games (app_id, name, last_updated)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    last_updated = VALUES(last_updated);
            """
            cur.execute(insert_query, game_data)
            print(f"Data for App ID {game_data[0]} inserted or updated.")

        # Commit the transaction to make the changes permanent
        conn.commit()

except Error as e:
    print(f"❌ Connection Failed: {e}")
    print("Check your RDS endpoint, credentials, and Security Group inbound rules.")

finally:
    # Close the connection if it was successfully established
    if conn and conn.is_connected():
        conn.close()
        print("Connection closed.")
