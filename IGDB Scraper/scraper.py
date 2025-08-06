__version__ = "0.1"
# Importing Libraries
import sys
import os
import re
import requests
import json
import time
import traceback
import argparse
from random import shuffle
import pymysql
from pymysql.cursors import DictCursor
import datetime as dt
import logging
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

CONFIG_FILE = 'config.yaml'
ENDPOINT_FILE = 'end_points.yaml'

# Loading Config File
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    logging.error(f"{CONFIG_FILE} not found")
    print(f"{CONFIG_FILE} not found")
    raise
except yaml.YAMLError as e:
    logging.error(f"Error parsing {CONFIG_FILE}: {e}")
    print(f"Error parsing {CONFIG_FILE}")
    raise

# Loading EndPoint File
try:
    with open(ENDPOINT_FILE, 'r', encoding='utf-8') as f:
        ENDPOINTS = yaml.safe_load(f)
except FileNotFoundError:
    logging.error(f"{ENDPOINT_FILE} not found")
    print(f"{ENDPOINT_FILE} not found")
    raise
except yaml.YAMLError as e:
    logging.error(f"Error parsing {ENDPOINT_FILE}: {e}")
    print(f"Error parsing {ENDPOINT_FILE}")
    raise

load_dotenv()
APPLIST_CACHE_FILE = 'applist.json'
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname).1s %(asctime)s] %(message)s',
    datefmt='%h:%M:%S'
)

class SteamAPI:
    def __init__(self, steam_api_config: dict, scraper_settings: dict) -> None:
        self.config = steam_api_config
        self.settings = scraper_settings
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'SteamScraper/{__version__}'})

    def _do_requests(self, url: str, params: Optional[dict] = None) -> dict:
        try:
            response = self.session.get(url, params = params, timeout = self.settings['timeout'])
            response.raise_for_status()
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
        return data[appid]['data'] if data[appid]['success'] else None

    def get_steamspy_details(self, appid: str) -> Optional[dict]:
        data = self._do_requests(f"https://steamspy.com/api.php?request=appdetails&appid={appid}")
        return data if data and data.get('developer') else None

    def get_achievements(self, appid: str) -> list:
        schema_data = self._do_requests(ENDPOINTS['STEAM']['GET_SCHEMA_FOR_GAME'], params={'appid': appid, 'l': self.config['language']})
        if not schema_data or 'game' not in schema_data or 'availableGameStats' not in schema_data['game']: return []
        achievements = schema_data['game']['availableGameStats'].get('achievements', [])
        if not achievements: return []
        percent_data = self._do_requests("http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/", params={'gameid': appid})
        percentages = {item['name']: item['percent'] for item in percent_data.get('achievementpercentages', {}).get('achievements', [])} if percent_data else {}
        return [{"app_id": int(appid), "api_name": a['name'], "display_name": a.get('displayName'), "description": a.get('description'), "global_completion_rate": round(percentages.get(a['name'], 0.0), 4)} for a in achievements]


    def get_reviews(self, appid: str) -> list:
        params = {'json': 1, 'num_per_page': 20,
            'language': 'English', 'filter_offtopic_activity': True,
            'filter_user_generated_content': True}
        data = self._do_requests(ENDPOINTS['STEAM']['GET_USER_REVIEW'] + f"{appid}", params)
        reviews = data["reviews"] if data["reviews"] and data.get('success') == 1 else []
        rev = []
        for r in reviews:
            rev.append(r)
        return rev

class IGDB_API(SteamAPI):
    def __init__(self, scraper_settings):
        super().__init__(steam_api_config={}, scraper_settings=scraper_settings)
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.access_token = self._get_twitch_access_token()
        self.headers = {'Client-ID': self.client_id, 'Authorization': f'Bearer {self.access_token}'} if self.access_token else {}

    def _get_twitch_access_token(self) -> Optional[str]:
        url = ENDPOINTS['TWITCH']['TWITCH_ACCESS_TOKEN']
        params = {"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "client_credentials"}
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            logging.info("Successfully obtained Twitch/IGDB access token.")
            return response.json().get("access_token")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get Twitch access token: {e}")
            return None

    def fetch_time_to_beat_by_name(self, game_name: str) -> Optional[dict]:
        if not self.headers: return None
        better_name = game_name.replace('"', '\\"')
        id_query = f"fields id; where name={better_name}; limit 1"
        game_data = requests.post(ENDPOINTS['TWITCH']['IGDB_GAME_URL'], headers=self.headers, data=id_query)

        if not game_data:
            logging.debug(f"IGDB: Game '{game_name}' not found")
            return None
        game_id = game_data[0]['id'] #type: ignore

        time_query = f"fields normally, hastly, completely; where game_id = {game_id}; limit 1"



        ttb_data = requests.post(ENDPOINTS['TWITCH']['IGDB_TIME_TO_BEAT_URL'], headers=self.headers, data=time_query)
        if not ttb_data:
            logging.debug(f"IGDB: Time to beat data not found for game '{game_name}'")
            return None
        ttb = ttb_data[0] #type: ignore
        return {
            "main": round(ttb.get('hastly', 0) / 3600, 2) if ttb.get('hastly') else None,
            "extras": round(ttb.get('normally', 0) / 3600, 2) if ttb.get('normally') else None,
            "completionist": round(ttb.get('completely', 0) / 3600, 2) if ttb.get('completely') else None
        }

class DatabaseManager:
    """
    Creates all data
    """
    def __init__(self, schema_yaml_path: str = "schema.yaml"):
        self.schema = self._load_schema(schema_yaml_path)
        load_dotenv()
        try:
            self.connection = pymysql.connect(
                host=str(os.getenv("DB_HOST")),
                user=str(os.getenv("DB_USER")),
                password=str(os.getenv("DB_PASSWORD")),
                database=str(os.getenv("DB_NAME")),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
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
                print("Error Parsing YAML: ", e)
                raise
            except FileNotFoundError:
                print("File Not Found at: ", schema_yaml_path)
                raise
        else:
            print("No schema file provided")
            raise

    def _creates_tables(self):
        for table_name in self.schema['create_order']:
            try:
                self.cursor.execute(self.schema['tables'][table_name])
            except pymysql.Error as e:
                print("Can't Create Table: ", table_name, e)
                raise
            except Exception as e:
                print("Unexpected Error: ", e)
                raise
        self.connection.commit()

    def is_processed(self, app_id: int) -> bool:
        try:
            self.cursor.execute(self.schema['queries']['scrap_status']['is_processed'], (app_id, ))
            return self.cursor.fetchone() is not None
        except pymysql.Error as e:
            print("Can't Check Processing Status: ", e)
            raise
        except Exception as e:
            print("Unexpected Error: ", e)
            raise

    def get_processed_count(self) -> int:
        self.cursor.execute("SELECT COUNT(1) as count FROM scrape_status")
        result = self.cursor.fetchone()
        return result['count'] if result else 0

    def mark_as_processed(self, appid: int, status: str):
        self.cursor.execute(self.schema['queries']['scrap_status']['mark_as_processed'], (appid, status))

    def _get_or_create_id(self, table: str, name: str) -> int:
        sql_insert = self.schema['queries']['lookup_tables']['insert_ignore'].format(table=table)
        sql_select = self.schema['queries']['lookup_tables']['select_id'].format(table=table)
        self.cursor.execute(sql_insert, (name,))
        self.cursor.execute(sql_select, (name,))
        result = self.cursor.fetchone()
        return result['id'] if result else -1

    def add_app_and_relations(self, parsed_data: dict):
        self.cursor.execute(self.schema['queries']['apps']['insert'], parsed_data)
        app_id = parsed_data['main']['id']
        for item_type in ['developers', 'publishers', 'genres', 'categories']:
            sql_link = self.schema['queries']['junction_tables']['insert_ignore'].format(table = f'app_{item_type}')
            for name in parsed_data.get(item_type, []):
                item_id = self._get_or_create_id(f'{item_type}s', name)
                if item_id != 1: self.cursor.execute(sql_link, (app_id, item_id))
        sql_link_lang = self.schema['queries']['junction_tables']['insert_language']
        for lang_name in parsed_data.get('supported_languages', []):
            is_audio = lang_name in parsed_data.get('full_audio_languages', [])
            lang_id = self._get_or_create_id('languages', lang_name)
            if lang_id != 1:
                self.cursor.execute(sql_link_lang, (app_id, lang_id, is_audio))
        sql_link_tag = self.schema['queries']['junction_tables']['insert_tag']
        for tag_name, tag_value in parsed_data.get('tags', {}).items():
            tag_id = self._get_or_create_id('tags', tag_name)
            if tag_id != 1:
                self.cursor.execute(sql_link_tag, (app_id, tag_id, tag_value))

    def add_achievements(self, achievements: list):
        if not achievements: return
        sql = self.schema['queries']['achievements']['insert_update']
        data = [(a['app_id'], a['api_name'], a['display_name'], a['description'], a['global_completion_rate']) for a in achievements]
        self.cursor.executemany(sql, data)

    def add_reviews(self, reviews: list):
        if not reviews: return
        sql_insert_review = self.schema['queries']['reviews']['insert_update']
        sql_link_review = self.schema['queries']['junction_tables']['insert_review_link']
        review_tuples, link_tuples = [], []

        for r in reviews:
            review_tuples.append((
                r['recommendationid'], r.get('author', {}).get('steamid'), r.get('language'),
                SteamScraperApplication.sanitize_text(r.get('review')), r.get('voted_up'),
                r.get('votes_up'), r.get('votes_funny'), dt.datetime.fromtimestamp(r.get('timestamp_created'))
            ))
            link_tuples.append((r['app_id'], r['recommendationid']))
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
        self.db = DatabaseManager()
        self.steam_api = SteamAPI(CONFIG['steam_api'], CONFIG['scraper_settings'])
        self.igdb_api = IGDB_API(CONFIG['scraper_settings'])

    def _load_and_validate_credentials(self):
        logging.info("Loading Credentials from .env file")
        db_creds = {
            'host': CONFIG['db_host'],
            'user': CONFIG['db_user'],
            'password': CONFIG['db_password'],
            'database': CONFIG['db_name']
        }
        igdb_creds = {
            'client_id': CONFIG['igdb_client_id'],
            'client_secret': CONFIG['igdb_client_secret']
        }

        logging.info("Credentials loaded successfully")
        return db_creds, igdb_creds

    def run(self):
        logging.info(f"Steam Scraper {__version__} starting.")

        app_ids = self.steam_api.get_all_app_ids()
        if not app_ids:
            logging.error("Could not retrieve app list, Exiting. ")
            sys.exit(1)

        total_apps = len(app_ids)
        processed_in_db = self.db.get_processed_count()
        logging.info(f"Found {total_apps} total apps on steam.")
        logging.info(f"Resuming progress. Found {processed_in_db} apps in database.")
        shuffle(app_ids)

        newly_processed_count = 0
        try:
            for i, appid_str in enumerate(app_ids):
                appid = int(appid_str)
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

                use_steamspy = CONFIG['scraper_settings']['use_steamspy']
                spy_details = self.steam_api.get_steamspy_details(appid_str) if use_steamspy and app_type == 'game' else None
                parsed_data = self._parse_app_data(app_details, spy_details)

                self.db.add_app_and_relations(parsed_data)

                if app_type == "game":
                    game_name = parsed_data['name']
                    if game_name:
                        time_data = self.igdb_api.fetch_time_to_beat_by_name(game_name)
                        if time_data: self.db.update_time_to_beat(appid, time_data)
                    if parsed_data['main']['achievements_count'] > 0:
                        self.db.add_achievements(self.steam_api.get_achievements(appid_str))
                self.db.add_reviews(self.steam_api.get_reviews(appid_str))

                self.db.mark_as_processed(appid, 'success'); self.db.commit()
                newly_processed_count += 1
                time.sleep(sleep_time)
        except (KeyboardInterrupt, SystemExit): print("\n"); logging.warning("Shutdown signal received...")
        except Exception: print("\n"); logging.error(f"An unexpected error occurred: {traceback.format_exc()}")
        finally:
            self.show_progress_bar('Finished', total_apps, total_apps, newly_processed_count)
            print("\n"); logging.info(f"Scrape session concluded. Processed {newly_processed_count} new apps.")
            self.db.close()

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
        if 'price_overview' in app_details: main_data['price'] = self.price_to_float(app_details['price_overview'].get('final_formatted', ''))
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
            langs = [lang.strip() for lang in SteamScraperApplication.sanitize_text(app_details['supported_languages']).split(',') if lang.strip()]
            for lang in langs:
                clean_lang = lang.replace('*', '').strip()
                if clean_lang:
                    supported_languages.append(clean_lang)
                    if lang.endswith('*'): full_audio_languages.append(clean_lang)
            return {
                        'main': main_data, 'developers': app_details.get('developers', []), 'publishers': app_details.get('publishers', []),
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
    scraper = SteamScraperApplication()
    scraper.run()
    logging.info("Done")
