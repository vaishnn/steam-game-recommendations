__version__ = "0.1"
# Importing Libraries
import sys
import os
import re
import requests
import json
import time
import traceback
from random import shuffle
import pymysql
import datetime as dt
import logging
import argparse
import shutil
from copy import deepcopy
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

CONFIG_FILE = 'config.yaml'
ENDPOINT_FILE = 'end_points.yaml'
CONFIG = {}
ENDPOINTS = {}
# Loading Config File
def load_config_file():
    try:

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            global CONFIG
            CONFIG = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"{CONFIG_FILE} not found")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {CONFIG_FILE}: {e}")
        raise

# Loading EndPoint File
def load_endpoints_file():
    try:
        with open(ENDPOINT_FILE, 'r', encoding='utf-8') as f:
            global ENDPOINTS
            ENDPOINTS = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"{ENDPOINT_FILE} not found")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {ENDPOINT_FILE}: {e}")
        raise

load_dotenv()
APPLIST_CACHE_FILE = 'applist.json'
# All about Logging
def manage_log_files():
    log_dir = ".old_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        logging.info(f"Created log directory: {log_dir}")
    for filename in os.listdir('.'):
        if filename.startswith("scraper_log_") and filename.endswith(".log"):
            shutil.move(filename, os.path.join(log_dir, filename))
            logging.info(f"Archived old log files: {filename}")
    return f"scraper_log_{dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

log_filename = manage_log_files()
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname).1s %(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename),      # Sends log messages to the file.
        logging.StreamHandler(sys.stdout)       # Sends log messages to the console.
    ]
)

class SteamAPI:
    """
    Handles all steam related stuff
    """
    def __init__(self, steam_api_config: dict, scraper_settings: dict) -> None:
        self.config = steam_api_config
        self.settings = scraper_settings
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'SteamScraper/{__version__}'})
        logging.info("SteamAPI initialized")

    def _do_requests(self, url: str, params: Optional[dict] = None) -> dict:
        try:
            response = self.session.get(url, params = params, timeout = self.settings['timeout'])
            response.raise_for_status()
            logging.info(f"Request SteamAPI successful: {response.status_code}")
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return {}

    def get_all_app_ids(self)-> List[str]:
        if os.path.exists(APPLIST_CACHE_FILE):
            logging.info(f"Loading Applist from Cache: {APPLIST_CACHE_FILE}")
            with open(APPLIST_CACHE_FILE, 'r', encoding = 'utf-8') as f:
                return json.load(f)
        logging.info("Requesting full app list from Steam API")
        app_list_data = self._do_requests(ENDPOINTS["STEAM"]["GET_APP_LIST"])
        app_ids = [str(data['appid']) for data in app_list_data['applist']['apps']]
        logging.info(f"Saying {len(app_ids)} app IDS to cache for future runs.")
        with open(APPLIST_CACHE_FILE, 'w', encoding = 'utf-8') as f:
            json.dump(app_ids, f)
        return app_ids

    def get_app_details(self, appid: str) -> Optional[dict]:
        params = {"appids": appid, "cc": self.config['currency'], "l":self.config['language']}
        data = self._do_requests(f"{ENDPOINTS['STEAM']['GET_APP_DETAILS']}", params)
        if not data:
            return None
        return data[appid]['data'] if data[appid]['success'] else None

    def get_steamspy_details(self, appid: str) -> Optional[dict]:
        data = self._do_requests(f"https://steamspy.com/api.php?request=appdetails&appid={appid}")
        return data if data and data.get('developer') else None

    def get_achievements(self, appid: str) -> list:
        schema_data = self._do_requests(
            ENDPOINTS['STEAM']['GET_SCHEMA_FOR_GAME'],
            params={'key': os.getenv('STEAM_API_KEY'), 'appid': appid, 'l': self.config['language']})
        if not schema_data or 'game' not in schema_data or 'availableGameStats' not in schema_data['game']: return []
        achievements = schema_data['game']['availableGameStats'].get('achievements', [])
        if achievements == []: return []
        percent_data = self._do_requests("http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/",
            params={'gameid': appid})
        percentages = {item['name']: item['percent']
            for item in percent_data.get('achievementpercentages', {}).get('achievements', [])} if percent_data else {}
        return [{"app_id": int(appid), "api_name": a['name'],
            "display_name": a.get('displayName'), "description": a.get('description'),
            "global_completion_rate": round(float(percentages.get(a['name'], 0.0)), 4)} for a in achievements]


    def get_reviews(self, appid: str) -> list:
        params = {'json': 1, 'num_per_page': 20,
            'language': 'english', 'filter_offtopic_activity': True,
            'filter_user_generated_content': True}
        data = self._do_requests(ENDPOINTS['STEAM']['GET_USER_REVIEW'] + f"{appid}", params)
        if data.get("reviews", []) == []:
            return []
        reviews = data["reviews"] if data["reviews"] and data.get('success') == 1 else []
        rev = []
        for r in reviews:
            rev.append(r)
        return rev

# class IGDB_API(SteamAPI):
#     def __init__(self, scraper_settings):
#         super().__init__(steam_api_config={}, scraper_settings=scraper_settings)
#         self.client_id = os.getenv("TWITCH_CLIENT_ID")
#         self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
#         self.access_token = self._get_twitch_access_token()
#         self.headers = {'Client-ID': self.client_id, 'Authorization': f'Bearer {self.access_token}'} if self.access_token else {}

#     def _get_twitch_access_token(self) -> Optional[str]:
#         url = ENDPOINTS['TWITCH']['TWITCH_ACCESS_TOKEN']
#         params = {"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "client_credentials"}
#         try:
#             response = requests.post(url, params=params)
#             response.raise_for_status()
#             logging.info("Successfully obtained Twitch/IGDB access token.")
#             return response.json().get("access_token")
#         except requests.exceptions.RequestException as e:
#             logging.error(f"Failed to get Twitch access token: {e}")
#             return None

#     def fetch_time_to_beat_by_name(self, game_name: str) -> Optional[dict]:
#         if not self.headers: return None
#         better_name = game_name.replace('"', '\\"')
#         id_query = f"fields id; where name={better_name}; limit 1"
#         game_data = requests.post(ENDPOINTS['TWITCH']['IGDB_GAME_URL'], headers=self.headers, data=id_query)

#         if not game_data:
#             logging.debug(f"IGDB: Game '{game_name}' not found")
#             return None
#         game_id = game_data[0]['id'] #type: ignore

#         time_query = f"fields normally, hastly, completely; where game_id = {game_id}; limit 1"



#         ttb_data = requests.post(ENDPOINTS['TWITCH']['IGDB_TIME_TO_BEAT_URL'], headers=self.headers, data=time_query)
#         if not ttb_data:
#             logging.debug(f"IGDB: Time to beat data not found for game '{game_name}'")
#             return None
#         ttb = ttb_data[0] #type: ignore
#         return {
#             "main": round(ttb.get('hastly', 0) / 3600, 2) if ttb.get('hastly') else None,
#             "extras": round(ttb.get('normally', 0) / 3600, 2) if ttb.get('normally') else None,
#             "completionist": round(ttb.get('completely', 0) / 3600, 2) if ttb.get('completely') else None
#         }

class DatabaseManager:
    """
    Creates all data
    """
    def __init__(self, db_creds: dict, schema_yaml_path: str = "schema.yaml"):
        self.schema = self._load_schema(schema_yaml_path)
        load_dotenv()
        try:
            self.connection = pymysql.connect(
                host=db_creds['host'], user=db_creds['user'], password=db_creds['password'],
                database=db_creds['database'], cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4'
            )
            self.cursor = self.connection.cursor()
            self._creates_tables()
        except pymysql.Error as e:
            logging.error(f"Database connection failed: {e}")
            sys.exit(1)

    def _load_schema(self, schema_yaml_path: str) -> dict:
        if schema_yaml_path:
            try:
                with open(schema_yaml_path, 'r') as file:
                    schema = yaml.safe_load(file)
                return schema
            except yaml.YAMLError as e:
                logging.error("Error Parsing YAML: ", e)
                raise
            except FileNotFoundError:
                logging.error("File Not Found at: ", schema_yaml_path)
                raise
        else:
            logging.error("No schema file provided")
            raise

    def get_all_processed_app_ids(self) -> set:
        logging.info("Fetching all processed app IDs...")
        self.cursor.execute(self.schema['queries']['scrape_status']['all_prcoessed'])
        processed_ids = {row['appid'] for row in self.cursor.fetchall()}
        logging.info(f"Found {len(processed_ids)} processed app IDs")
        return processed_ids

    def _drop_all_tables(self):
        """
        Drops all application tables from the database in the correct order.
        This is a destructive operation and should be used with caution.
        """
        try:
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            logging.warning("Attempting to drop all scraper tables...")
            for table_name in self.schema['drop_order']:
                logging.info(f"Dropping table: {table_name}...")
                self.cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            logging.info("All tables dropped successfully.")
        except pymysql.Error as err:
            logging.error(f"An error occurred while dropping tables: {err}")
        finally:
            # Always re-enable foreign key checks.
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            self.connection.commit()

    def _creates_tables(self):
        for table_name in self.schema['create_order']:
            try:
                self.cursor.execute(self.schema['tables'][table_name])
            except pymysql.Error as e:
                logging.error(f"An error occurred while creating table {table_name}: {e}")
                raise
            except Exception as e:
                logging.error(f"An unexpected error occurred while creating table {table_name}: {e}")
                raise
        self.connection.commit()

    def is_processed(self, app_id: int) -> bool:
        try:
            self.cursor.execute(self.schema['queries']['scrape_status']['is_processed'], (app_id, ))
            return self.cursor.fetchone() is not None
        except pymysql.Error as e:
            logging.error(f"An error occurred while checking processing status for app_id {app_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred while checking processing status for app_id {app_id}: {e}")
            raise

    def get_processed_count(self) -> int:
        self.cursor.execute("SELECT COUNT(1) as count FROM scrape_status")
        result = self.cursor.fetchone()
        return result['count'] if result else 0

    def mark_as_processed(self, appid: int, status: str):
        self.cursor.execute(self.schema['queries']['scrape_status']['mark_processed'], (appid, status))

    def _get_or_create_id(self, table: str, name: str) -> int:
        sql_insert = self.schema['queries']['lookup_tables']['insert_ignore'].format(table=table)
        sql_select = self.schema['queries']['lookup_tables']['select_id'].format(table=table)
        self.cursor.execute(sql_insert, (name,))
        self.cursor.execute(sql_select, (name,))
        result = self.cursor.fetchone()
        return result['id'] if result else -1

    def add_pending_dlc_link(self, dlc_id: int, base_game_id: int):
        logging.info(f"Adding pending DLC link for DLC ID {dlc_id} and base game ID {base_game_id}")
        sql = self.schema['queries']['junction_tables']['add_pending_dlc']
        self.cursor.execute(sql, (dlc_id, base_game_id))

    def resolve_pending_dlc_links(self):
        logging.info("Attempting to resolve pending DLC links")
        try:
            sql_resolve = self.schema['queries']['utility_queries']['resolve_dlc_links']
            self.cursor.execute(sql_resolve)
            resolved_count = self.cursor.rowcount
            if resolved_count > 0:
                logging.info(f"Resolved {resolved_count} pending DLC links")
            else:
                logging.info("No pending DLC links to resolve")
            sql_clear = self.schema['queries']['utility_queries']['clear_resolved_dlc_links']
            self.cursor.execute(sql_clear)
            self.connection.commit()
        except Exception as e:
            logging.error(f"Failed to resolve pending DLC links: {e}")

    def add_app_and_relations(self, parsed_data: Dict[str, Any]):
        """Inserts/updates an app in the master `apps` table, then links all its related data."""
        # --- THIS IS THE CRUCIAL FIX ---
        # We now pass the 'main_tuple' to the execute command, which matches the '%s' placeholders.
        self.cursor.execute(self.schema['queries']['apps']['insert_update'], parsed_data['main_tuple'])

        # The app's ID is the first item in the tuple.
        app_id = parsed_data['main_tuple'][0]

        # The rest of the logic for linking related data remains the same.
        for item_type in ['developers', 'publishers', 'categories', 'genres']:
            sql_link = self.schema['queries']['junction_tables']['insert_ignore'].format(table=f'app_{item_type}')
            for name in parsed_data.get(item_type, []):
                item_id = self._get_or_create_id(item_type, name)
                if item_id != -1: self.cursor.execute(sql_link, (app_id, item_id))

        sql_link_lang = self.schema['queries']['junction_tables']['insert_language']
        for lang_name in parsed_data.get('supported_languages', []):
            is_audio = lang_name in parsed_data['main_dict'].get('full_audio_languages', [])
            lang_id = self._get_or_create_id('languages', lang_name)
            if lang_id != -1: self.cursor.execute(sql_link_lang, (app_id, lang_id, is_audio))

        sql_link_tag = self.schema['queries']['junction_tables']['insert_tag']
        if isinstance(parsed_data.get('tags', {}), list):
            print(parsed_data.get('tags', {}))
        for tag_name, tag_value in ({} if isinstance(parsed_data.get('tags', {}), list) else parsed_data.get('tags', {})).items():
            tag_id = self._get_or_create_id('tags', tag_name)
            if tag_id != -1: self.cursor.execute(sql_link_tag, (app_id, tag_id, tag_value))

    def add_achievements(self, achievements: list):
        if not achievements: return
        sql = self.schema['queries']['achievements']['insert_update']
        data = [(a['app_id'], a['api_name'], a['display_name'],
            a['description'], a['global_completion_rate']) for a in achievements]
        self.cursor.executemany(sql, data)

    def add_reviews(self, reviews: list, app_id: str):
        if not reviews: return
        sql_insert_review = self.schema['queries']['reviews']['insert_update']
        sql_link_review = self.schema['queries']['junction_tables']['insert_reviews']
        review_tuples, link_tuples = [], []

        for r in reviews:
            review_tuples.append((
                r['recommendationid'], r.get('author', {}).get('steamid'), r.get('language'),
                SteamScraperApplication.sanitize_text(r.get('review')), r.get('voted_up'),
                r.get('votes_up'), r.get('votes_funny'), dt.datetime.fromtimestamp(r.get('timestamp_created'))
            ))
            link_tuples.append((app_id, r['recommendationid']))
        if review_tuples:
            self.cursor.executemany(sql_insert_review, review_tuples)
        if link_tuples:
            self.cursor.executemany(sql_link_review, link_tuples)

    def update_time_to_beat(self, appid: int, time_data: dict):
        sql = self.schema['queries']['apps']['update_time_to_beat']
        self.cursor.execute(sql, (time_data.get('main'), time_data.get('extras'), time_data.get('completionist'), appid))

    def commit(self):
        self.connection.commit()

    def close(self):
        if self.connection and self.connection.open:
            self.connection.commit()
            self.cursor.close()
            self.connection.close()
            logging.info("Database connection closed")

class SteamScraperApplication:
    def __init__(self):
        self.args = self._setup_arg_parser()
        db_creds, steam_api_key = self._load_and_validate_credentials()
        self.db = DatabaseManager(db_creds)
        self.steam_api = SteamAPI(CONFIG['steam_api'], CONFIG['scraper_settings'])

        # self.igdb_api = IGDB_API(CONFIG['scraper_settings'])

    def _load_and_validate_credentials(self):
        logging.info("Loading credentials from .env file...")
        db_vars = {'host': 'DB_HOST', 'user': 'DB_USER', 'password': 'DB_PASSWORD', 'database': 'DB_NAME'}
        db_creds = {key: os.getenv(env_var) for key, env_var in db_vars.items()}

        steam_api_key = os.getenv('STEAM_API_KEY')

        all_creds = {**db_creds, 'steam_api_key': steam_api_key}
        for key, value in all_creds.items():
            if not value:
                logging.error(f"FATAL: Required credential for '{key.upper()}' not set in your .env file.")
                sys.exit(1)

        logging.info("Credentials loaded successfully.")
        return db_creds, steam_api_key

    def run(self):
        logging.info(f"Steam Scraper {__version__} starting.")

        app_ids = self.steam_api.get_all_app_ids()
        if not app_ids:
            logging.error("Could not retrieve app list, Exiting. ")
            sys.exit(1)


        processed_in_db = self.db.get_processed_count()
        processed_id_set = self.db.get_all_processed_app_ids()
        __temp_id = deepcopy(app_ids)
        for appid in app_ids:
            if int(appid) in processed_id_set:
                __temp_id.remove(appid)
        app_ids = [str(appid) for appid in __temp_id]
        total_apps = len(app_ids)
        logging.info(f"Found {total_apps} total apps on steam.")
        logging.info(f"Resuming progress. Found {processed_in_db} apps in database.")
        shuffle(app_ids)

        newly_processed_count = 0
        try:
            for i, appid_str in enumerate(app_ids):
                appid = int(appid_str)
                if self.args.pre_filter:
                    if appid in processed_id_set:
                        self.show_progress_bar('Scraping', i + 1, total_apps, newly_processed_count)
                        continue
                self.show_progress_bar('Scraping', i + 1, total_apps, newly_processed_count)
                if self.db.is_processed(appid):
                    sys.stdout.write('.');
                    sys.stdout.flush()
                    continue

                app_details = self.steam_api.get_app_details(appid_str)
                sleep_time = CONFIG['scraper_settings']['sleep']
                time.sleep(sleep_time/2.0)

                if not app_details:
                    self.db.mark_as_processed(appid, 'unavailable')
                    self.db.commit()
                    continue

                app_type = app_details.get('type')
                if app_type not in ['game', 'dlc']:
                    self.db.mark_as_processed(appid, f"skipped type: {app_type}")
                    continue

                use_steamspy = CONFIG['scraper_settings']['use_steamspy']
                spy_details = self.steam_api.get_steamspy_details(appid_str) if use_steamspy and app_type == 'game' else None
                parsed_data = self._parse_app_data(app_details, spy_details)

                self.db.add_app_and_relations(parsed_data)

                self.db.commit()
                if parsed_data.get('base_game_id'):
                   self.db.add_pending_dlc_link(appid, parsed_data['base_game_id'])


                if app_type == "game":
                    # game_name = parsed_data['main_dict']['name']
                    # if game_name:
                    #     time_data = self.igdb_api.fetch_time_to_beat_by_name(game_name)
                    #     if time_data: self.db.update_time_to_beat(appid, time_data)
                    if parsed_data['main_dict']['achievements_count'] > 0:
                        self.db.add_achievements(self.steam_api.get_achievements(appid_str))
                self.db.add_reviews(self.steam_api.get_reviews(appid_str), appid_str)

                self.db.mark_as_processed(appid, 'success'); self.db.commit()
                newly_processed_count += 1
                time.sleep(sleep_time)
        except (KeyboardInterrupt, SystemExit): print("\n"); logging.warning("Shutdown signal received...")
        except Exception: print("\n"); logging.error(f"An unexpected error occurred: {traceback.format_exc()}")
        finally:

            self.db.resolve_pending_dlc_links()
            self.show_progress_bar('Finished', total_apps, total_apps, newly_processed_count)
            print("\n"); logging.info(f"Scrape session concluded. Processed {newly_processed_count} new apps.")
            self.db.close()

    def _setup_arg_parser(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description=f'Steam Scraper {__version__}',
            formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--drop-tables', action='store_true',
            help='Drop all scraper tables from the database and exit.')
        parser.add_argument('--pre-filter', action='store_true',
            help='Pre-filter which are already processed')
        return parser.parse_args()

    def _parse_app_data(self, app_details: dict, spy_details: Optional[dict]) -> dict:
        appid = app_details['steam_appid']
        app_type = app_details.get('type')
        main_data = {
            'id': appid, 'type': app_details.get('type'), 'name': SteamScraperApplication.sanitize_text(app_details.get('name')),
            'base_game_id': app_details.get('fullgame', {}).get('appid'),
            'release_date': self.parse_steam_date(app_details.get('release_date', {}).get('date', '')),
            'price': 0.0, 'positive_reviews': 0, 'negative_reviews': 0, 'recommendations': 0, 'peak_ccu': 0,
            'metacritic_score': 0, 'metacritic_url': None, 'required_age': 0, 'achievements_count': 0,
            'supports_windows': False, 'supports_mac': False, 'supports_linux': False,
            'header_image_url': app_details.get('header_image'), 'estimated_owners': None, 'user_score': 0, 'score_rank': None,
            'about_the_game': SteamScraperApplication.sanitize_text(app_details.get('about_the_game')),
            'detailed_description': SteamScraperApplication.sanitize_text(app_details.get('detailed_description')),
            'short_description': SteamScraperApplication.sanitize_text(app_details.get('short_description')),
            'reviews_summary': SteamScraperApplication.sanitize_text(app_details.get('reviews'))
        }
        if 'price_overview' in app_details: main_data['price'] = self.price_to_float(
            app_details['price_overview'].get('final_formatted', ''))
        if 'recommendations' in app_details: main_data['recommendations'] = app_details['recommendations'].get('total', 0)
        if 'metacritic' in app_details:
            main_data['metacritic_score'] = app_details['metacritic'].get('score', 0)
            main_data['metacritic_url'] = app_details['metacritic'].get('url')
        if 'platforms' in app_details:
            main_data.update({
                'supports_windows': app_details['platforms'].get('windows', False),
                'supports_mac': app_details['platforms'].get('mac', False),
                'supports_linux': app_details['platforms'].get('linux', False)
            })

        if app_type == "game":
            main_data['required_age'] = int(str(app_details.get('required_age', '0')).replace('+', ''))
            if 'achievements' in app_details:
                main_data['achievements_count'] = app_details['achievements'].get('total', 0)

            if spy_details:
                main_data.update({
                    'positive_reviews': spy_details.get('positive', 0), 'negative_reviews': spy_details.get('negative', 0),
                    'peak_ccu': spy_details.get('ccu', 0), 'estimated_owners': spy_details.get('owners', '0 - 20000').replace(',', ''),
                    'user_score': spy_details.get('userscore', 0), 'score_rank': spy_details.get('score_rank', '')
                })

        supported_languages, full_audio_languages = [], []
        langs = [lang.strip()
            for lang in SteamScraperApplication.sanitize_text(
                app_details.get("supported_languages", "")).split(',') if lang.strip()]
        for lang in langs:
            clean_lang = lang.replace('*', '').strip()
            if clean_lang:
                supported_languages.append(clean_lang)
                if lang.endswith('*'): full_audio_languages.append(clean_lang)
        main_data_tuple = (
                    main_data['id'], main_data['type'], main_data['name'],
                    main_data['release_date'], main_data['price'], main_data['positive_reviews'],
                    main_data['negative_reviews'], main_data['recommendations'], main_data['peak_ccu'],
                    main_data['metacritic_score'], main_data['metacritic_url'], main_data['required_age'],
                    main_data['achievements_count'], main_data['supports_windows'], main_data['supports_mac'],
                    main_data['supports_linux'], main_data['header_image_url'], main_data['estimated_owners'],
                    main_data['user_score'], main_data['score_rank'], main_data['about_the_game'],
                    main_data['detailed_description'], main_data['short_description'], main_data['reviews_summary']
                )

        return {
            'main_tuple': main_data_tuple,  # Use this tuple for the main INSERT operation.
            'main_dict': main_data,       # Keep the dict for easy access to values by name (like 'name' for IGDB).
            'base_game_id': app_details.get('fullgame', {}).get('appid'),
            'developers': app_details.get('developers', []), 'publishers': app_details.get('publishers', []),
            'categories': [c['description'] for c in app_details.get('categories', [])],
            'genres': [g['description'] for g in app_details.get('genres', [])],
            'supported_languages': supported_languages, 'full_audio_languages': full_audio_languages,
            'tags': spy_details.get('tags', {}) if spy_details else {}
        }
    @staticmethod
    def sanitize_text(text: Optional[str]) -> str:
        if not text:
            return ''
        text = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return re.sub(r'<[^>]*>', ' ', text).replace('&quot;', '"').replace('&amp;', '&').strip()

    @staticmethod
    def parse_steam_date(date_str: str):
        if not date_str or 'coming_soon' in date_str: return None
        cleaned_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str.replace(',', ''))
        try:
            return dt.datetime.strptime(cleaned_date, '%d %b %Y').strftime('%Y-%m-%d')
        except ValueError:
            try: return dt.datetime.strptime(cleaned_date, '%b %d %Y').strftime('%Y-%m-%d')
            except ValueError:
                return None

    @staticmethod
    def show_progress_bar(title: str, count: int, total: int, new_items: int):
        """Displays a dynamic progress bar in the console."""
        bar_len = 60
        filled_len = int(round(bar_len * count / float(total)))
        percents = round(100.0 * count / float(total), 2)
        bar = '█' * filled_len + '░' * (bar_len - filled_len)
        now_time = dt.datetime.now(dt.timezone.utc).astimezone().strftime('%H:%M:%S')
        sys.stdout.write(f"\r[I {now_time}] {title} {bar} {percents}% ({count}/{total}) | New This Session: {new_items}")
        sys.stdout.flush()

    @staticmethod
    def price_to_float(price_text: str) -> float:
        try:
            price_text = price_text.replace(',', '.')
            match = re.search(r'([0-9]+\.?[0-9]*)', price_text)
            return float(match.group(1)) if match else 0.0
        except (ValueError, AttributeError):
            return 0.0

if __name__ == '__main__':
    load_endpoints_file()
    load_config_file()
    scraper = SteamScraperApplication()

    if scraper.args.drop_tables:
        confirm = input("Are you sure you want to drop all scraper tables? This cannot be undone. (yes/no): ")
        if confirm.lower() == 'yes':
            scraper.db._drop_all_tables()
        else:
            print("Operation cancelled.")
    scraper.run()
    logging.info("Done")
