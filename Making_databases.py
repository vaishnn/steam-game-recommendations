import pymysql
import os
import json
from dotenv import load_dotenv
from datetime import datetime

class CreatingTables:
    def __init__(self):
        load_dotenv()
        self.connection = None
        self.DB_HOST = str(os.environ.get("DB_HOST"))
        self.DB_USER = str(os.environ.get("DB_USER"))
        self.DB_PASSWORD = str(os.environ.get("DB_PASSWORD"))
        self.DB_NAME = str(os.environ.get("DB_NAME"))
        self.DB_PORT = str(os.environ.get("DB_PORT"))

        if not all([self.DB_HOST, self.DB_USER, self.DB_PASSWORD, self.DB_NAME, self.DB_PORT]):
            raise ValueError("Missing environment variables")

        try:
            self.connection = pymysql.connect(
                host = self.DB_HOST,
                user = self.DB_USER,
                password = self.DB_PASSWORD,
                database = self.DB_NAME,
                port = int(self.DB_PORT)
            )
            print("Database Connection Established")
        except pymysql.Error as e:
            print(f"Error connecting to database: {e}")
            self.connection = None
            return

    def _execute_sql(self, query, params = None, fetch_one = False):
        """
        To Execute SQL Queries, it's in the name
        """
        if not self.connection:
            print("Database connection not established")
            return
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch_one:
                    return cursor.fetchone()

                if query.strip().upper().startswith(("INSERT", "UPDATE")):
                    return cursor.lastrowid
                return None
        except pymysql.Error as e:
            print(f"Error executing\n{query}\nSQL query: {e}")
            self.connection.rollback()
            raise
        finally:
            if self.connection and not self.connection.closed:
                return self.connection.commit()

    def drop_all_tables(self):
        print("\n-- Dropping all tables (if they exist) ---")

        drop_queries = [
            "DROP TABLE IF EXISTS user_achievements;",
            "DROP TABLE IF EXISTS achievements;",
            "DROP TABLE IF EXISTS game_reviews;",
            "DROP TABLE IF EXISTS game_rankings;",
            "DROP TABLE IF EXISTS user_game_interactions;",
            "DROP TABLE IF EXISTS users;", # Drop users before game_developers if game_developers references users (not in this schema, but good general practice)
            "DROP TABLE IF EXISTS game_developers;",
            "DROP TABLE IF EXISTS developers;",
            "DROP TABLE IF EXISTS game_publishers;",
            "DROP TABLE IF EXISTS publishers;",
            "DROP TABLE IF EXISTS game_categories;",
            "DROP TABLE IF EXISTS categories;",
            "DROP TABLE IF EXISTS game_genres;",
            "DROP TABLE IF EXISTS genres;",
            "DROP TABLE IF EXISTS game_audio_languages;",
            "DROP TABLE IF EXISTS game_supported_languages;",
            "DROP TABLE IF EXISTS languages;",
            "DROP TABLE IF EXISTS game_tags;",
            "DROP TABLE IF EXISTS tags;",
            "DROP TABLE IF EXISTS game_screenshots;",
            "DROP TABLE IF EXISTS package_subscriptions;",
            "DROP TABLE IF EXISTS game_packages;",
            "DROP TABLE IF EXISTS game_movies;",
            "DROP TABLE IF EXISTS games;" # Core games table last
        ]

        for query in drop_queries:
            try:
                self._execute_sql(query)
                print(f"Dropped: {query.split(' ')[4].strip(';')[0]} (if existed)")
            except Exception as e:
                print(f"Error {e} dropping table: {query.split(' ')[4].strip(';')[0]}")
                raise
        print(" -- Tables drop complete ---")

    def create_all_tables(self):
        print(" --- Creating all normalized tables --- ");
        create_queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL
            steam_id BIGINT UNIQUE,
            registration_date DATETIME NOT NULL,
            last_login DATETIME NOT NULL,
            user_preferences JSON NOT NULL,
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS games (
                            game_id INT PRIMARY KEY, -- Removed AUTO_INCREMENT
                            name VARCHAR(255) NOT NULL,
                            release_date DATE,
                            price DECIMAL(10, 2),
                            positive_reviews INT,
                            negative_reviews INT,
                            recommendations INT,
                            peak_ccu INT,
                            metacritic_score INT,
                            metacritic_url VARCHAR(512),
                            required_age INT,
                            dlc_count INT,
                            achievements_count INT,
                            avg_playtime_2weeks INT,
                            avg_playtime_forever INT,
                            median_playtime_2weeks INT,
                            median_playtime_forever INT,
                            supports_windows BOOLEAN,
                            supports_mac BOOLEAN,
                            supports_linux BOOLEAN,
                            header_image_url VARCHAR(512),
                            website_url VARCHAR(512),
                            support_url VARCHAR(512),
                            support_email VARCHAR(255),
                            estimated_owners VARCHAR(50),
                            user_score INT,
                            score_rank VARCHAR(50),
                            about_the_game TEXT,
                            detailed_description TEXT,
                            short_description TEXT,
                            reviews_summary TEXT,
                            notes TEXT
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS developers (
                            developer_id INT AUTO_INCREMENT PRIMARY KEY,
                            developer_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS publishers (
                            publisher_id INT AUTO_INCREMENT PRIMARY KEY,
                            publisher_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS categories (
                            category_id INT AUTO_INCREMENT PRIMARY KEY,
                            category_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS genres (
                            genre_id INT AUTO_INCREMENT PRIMARY KEY,
                            genre_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS languages (
                            language_id INT AUTO_INCREMENT PRIMARY KEY,
                            language_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS tags (
                            tag_id INT AUTO_INCREMENT PRIMARY KEY,
                            tag_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_developers (
                            game_id INT NOT NULL,
                            developer_id INT NOT NULL,
                            PRIMARY KEY (game_id, developer_id),
                            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                            FOREIGN KEY (developer_id) REFERENCES developers(developer_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_publishers (
                        game_id INT NOT NULL,
                        publisher_id INT NOT NULL,
                        PRIMARY KEY (game_id, publisher_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_categories (
                        game_id INT NOT NULL,
                        category_id INT NOT NULL,
                        PRIMARY KEY (game_id, category_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_genres (
                        game_id INT NOT NULL,
                        genre_id INT NOT NULL,
                        PRIMARY KEY (game_id, genre_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_audio_languages (
                        game_id INT NOT NULL,
                        language_id INT NOT NULL,
                        PRIMARY KEY (game_id, language_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (language_id) REFERENCES languages(language_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_supported_languages (
                        game_id INT NOT NULL,
                        language_id INT NOT NULL,
                        PRIMARY KEY (game_id, language_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (language_id) REFERENCES languages(language_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_tags (
                        game_id INT NOT NULL,
                        tag_id INT NOT NULL,
                        tag_value INT,
                        PRIMARY KEY (game_id, tag_id),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_screenshots (
                        screenshot_id INT AUTO_INCREMENT PRIMARY KEY,
                        game_id INT NOT NULL,
                        image_url VARCHAR(255) NOT NULL,
                        display_order INT,
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS user_game_interactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        game_id INT NOT NULL,
                        interaction_type VARCHAR(50) NOT NULL,
                        interaction_value DECIMAL(10,2),
                        interaction_date DATETIME NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
                        UNIQUE KEY user_game_interaction_unique (user_id, game_id, interaction_type)
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_reviews (
                        reviews_id INT AUTO_INCREMENT PRIMARY KEY,
                        game_id INT NOT NULL,
                        user_id INT,
                        external_reviewer_id VARCHAR(255),
                        review_text TEXT NOT NULL,
                        score INT,
                        is_recommended BOOLEAN,
                        review_date DATETIME NOT NULL,
                        review_source VARCHAR(255),
                        language VARCHAR(50),
                        votes_up INT DEFAULT 0,
                        votes_funny INT DEFAULT 0,
                        last_edited_date DATETIME,
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                        );
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS game_rankings (
                        ranking_entry_id INT AUTO_INCREMENT PRIMARY KEY,
                        game_id INT NOT NULL,
                        ranking_type VARCHAR(100) NOT NULL,
                        ranking_value DECIMAL(18,5) NOT NULL,
                        rank INT,
                        last_calculated_data DATETIME NOT NULL,
                        UNIQUE KEY game_ranking_type_unique (game_id, ranking_type),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
                        );
                        """
        ]

        for query in create_queries:
            table_name = query.split('TABLE IF NOT EXISTS ')[1].split(' ')[0]
            try:
                self._execute_sql(query)
                print(f"Table {table_name} created successfully.")
            except Exception as e:
                print(f"Error creating table {table_name}: {e}")
                raise
