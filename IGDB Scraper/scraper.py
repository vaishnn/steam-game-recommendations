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
import random
import pymysql
import datetime as dt
import logging
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

try:
    with open('end_points.yaml', 'r', encoding='utf-8') as f:
        ENDPOINTS = yaml.safe_load(f)
except FileNotFoundError:
    logging.error("end_points.yaml not found")
    print("end_points.yaml not found")
    raise
except yaml.YAMLError as e:
    logging.error(f"Error parsing end_points.yaml: {e}")
    print("Error parsing end_points.yaml")
    raise

load_dotenv()
CONFIG_FILE = 'config.yaml'
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

    def _do_requests(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
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
        data = self._do_requests(ENDPOINTS["STEAM"]["GET_APP_LIST"])
        app_ids = [str(data['appid']) for data in data['applist']['apps']]
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
        achievements_data = self._do_requests(ENDPOINTS['STEAM']['GET_USER_STATS_FOR_GAMES'], params = {'gameid': appid})
        if (achievements_data and achievements_data["achievementpercentages"] and
        achievements_data["achievementpercentages"]["achievements"]):
            return achievements_data["achievementpercentages"]["achievements"]
        return []

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
    def __init__(self):
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
        game_id = game_data[0]['id']

        time_query = f"fields normally, hastly, completely; where game_id = {game_id}; limit 1"



        ttb_data = requests.post(ENDPOINTS['TWITCH']['IGDB_TIME_TO_BEAT_URL'], headers=self.headers, data=time_query)
        if not ttb_data:
            logging.debug(f"IGDB: Time to beat data not found for game '{game_name}'")
            return None
        ttb = ttb_data[0]
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
        self.connection = None

    def _make_connection(self):
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
            print("Can't Connect to Database: ", e)
            raise

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
        self.cursor.execute("SELECT COUNT(")
        return 2

class SteamScraperApplication:
    def __init__(self):
        pass

    def _load_config(self):
        logging.info(f"Loading settings from '{CONFIG_FILE}'")

    def __setup_arg_parser(self):
        """
        Defines and Origanizes all non-sensitive command-line arguments.
        """

        parser = argparse.ArgumentParser(description = f'Steam Scraper {__version__}')
