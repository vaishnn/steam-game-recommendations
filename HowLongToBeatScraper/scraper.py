import requests
import argparse
import json
import yaml

class hltbScrapper:

    """
    To Scrape Data from HowLongToBeat
    Scrape Data Includes time of completion of games
    """
    def __init__(self, pathYAML = "end_points.yaml"):
        self.end_points = self.load_end_points(pathYAML)
        self.requests_headers = {
            'content-type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'referer': 'https://howlongtobeat.com/'
        }

    def load_end_points(self, pathYAML):
        if pathYAML:
            try:
                with open(pathYAML, 'r') as file:
                    return yaml.safe_load(file)
            except yaml.YAMLError as e:
                print(f"Error loading YAML file: {e}")
                raise
        else:
            print("No YAML file provided")
            raise
