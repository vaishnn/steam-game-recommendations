import pymysql
import dotenv
import os

dotenv.load_dotenv()

class table_creation:

    """
    This creates the following tables schema:
        - User Table
        - User Game Interaction Table
        - Game Data Table
    """
    def __init__(self, drop_table: bool):
        self.drop_table = drop_table
        self.loading_env()
        self.user_table_creation()
        self.video_game_table()
        self.user_game_interaction_data()

    def loading_env(self):
        self.db_host = str(os.getenv('DB_HOST'))
        self.db_user = str(os.getenv('DB_USER'))
        self.db_password = str(os.getenv('DB_PASSWORD'))
        self.db_name = str(os.getenv('DB_NAME'))

    def user_table_creation(self):
        connection = pymysql.connect(
            host = self.db_host,
            user = self.db_user,
            password = self.db_password,
            database = self.db_name,
            cursorclass = pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # if self.drop_table:
            #     cursor.execute("DROP TABLE IF EXISTS users")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY, -- Unique ID for each user
                username VARCHAR(255) UNIQUE NOT NULL, -- User's chosen username
                email VARCHAR(255) UNIQUE,             -- User's email (optional, can be NULL)
                steam_id BIGINT UNIQUE,                -- Link to Steam profile (if applicable)
                registration_date DATETIME,            -- When the user registered
                last_login DATETIME,                   -- Last time the user logged in
                user_preferences JSON                  -- Store more complex user preferences as JSON
            );
            """
            cursor.execute(create_table_sql)
            connection.commit()

    def video_game_table(self):
        connection = pymysql.connect(
            host = self.db_host,
            user = self.db_user,
            password = self.db_password,
            database = self.db_name,
            cursorclass = pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # if self.drop_table:
            #     cursor.execute("DROP TABLE IF EXISTS video_games")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS video_games (
                id INT AUTO_INCREMENT PRIMARY KEY, -- Unique identifier for each game
                name VARCHAR(255) NOT NULL,        -- Game title (e.g., 'Counter-Strike: Condition Zero')
                release_date DATE,                 -- Date of release (e.g., 'Mar 1, 2004')
                price DECIMAL(10, 2),              -- Price of the game
                positive_reviews INT,              -- Number of positive reviews
                negative_reviews INT,              -- Number of negative reviews
                recommendations INT,               -- Number of recommendations
                peak_ccu INT,                      -- Peak concurrent users
                metacritic_score INT,              -- Metacritic score
                metacritic_url VARCHAR(255),       -- URL to Metacritic page
                required_age INT,                  -- Required age
                dlc_count INT,                     -- Number of DLCs
                achievements INT,                  -- Number of achievements
                avg_playtime_2weeks INT,           -- Average playtime in last 2 weeks (minutes)
                avg_playtime_forever INT,          -- Average playtime forever (minutes)
                median_playtime_2weeks INT,        -- Median playtime in last 2 weeks (minutes)
                median_playtime_forever INT,       -- Median playtime forever (minutes)
                supports_windows BOOLEAN,          -- True if supports Windows
                supports_mac BOOLEAN,              -- True if supports Mac
                supports_linux BOOLEAN,            -- True if supports Linux
                header_image_url VARCHAR(255),     -- URL to the header image
                website_url VARCHAR(255),          -- Official website URL
                support_url VARCHAR(255),          -- Support URL
                support_email VARCHAR(255),        -- Support email
                estimated_owners VARCHAR(50),      -- Estimated owner range (e.g., '10000000 - 20000000')
                user_score INT,                    -- User score
                score_rank VARCHAR(50),            -- Score rank (empty in example)
                reviews_summary TEXT,              -- Reviews summary (empty in example, but can be long)
                notes TEXT,                        -- Notes (empty in example, but can be long)
                -- All other complex or less frequently queried fields stored as JSON
                game_details_json JSON
            );

            """
            cursor.execute(create_table_sql)
            connection.commit()

    def user_game_interaction_data(self):
        connection = pymysql.connect(
            host = self.db_host,
            user = self.db_user,
            password = self.db_password,
            database = self.db_name,
            cursorclass = pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # if self.drop_table:
            #     cursor.execute("DROP TABLE IF EXISTS user_game_interactions")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS user_game_interactions (
                id INT AUTO_INCREMENT PRIMARY KEY,     -- Unique ID for each interaction record
                user_id INT NOT NULL,                 -- Foreign key to the users table
                game_id INT NOT NULL,                 -- Foreign key to the video_games table
                interaction_type VARCHAR(50) NOT NULL, -- e.g., 'played', 'purchased', 'wishlisted', 'rated', 'viewed'
                interaction_value DECIMAL(10, 2),     -- e.g., playtime in minutes (for 'played'), rating (for 'rated')
                interaction_date DATETIME NOT NULL,   -- When the interaction occurred
                -- Optional: If you want to track more specific actions
                -- details JSON,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (game_id) REFERENCES video_games(id) ON DELETE CASCADE,
                -- Add a unique constraint to prevent duplicate interaction types for the same user-game pair within a time period
                -- For playtime, you'd likely update the existing record rather than insert a new one if it's cumulative.
                -- For 'purchased' or 'wishlisted', you'd typically have one record per user-game.
                UNIQUE KEY user_game_interaction_unique (user_id, game_id, interaction_type)
            );
            """
            cursor.execute(create_table_sql)
            connection.commit()

if __name__ == "__main__":
    tables = table_creation(True)
