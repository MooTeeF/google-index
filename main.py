import argparse
from datetime import datetime
import httplib2
from typing import List, Dict, Any
import os

import pandas as pd
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ["https://www.googleapis.com/auth/indexing"]


class Indexer:
   
    def __init__(self, urls: List[str], google_api_credential: str):
      self.urls = urls
      self.google_api_credential = google_api_credential
      self.successful_urls = []

    def api_callback(self, request_id, response, exception):
        if exception is None:
            self.successful_urls.append(dict(
                url=response['urlNotificationMetadata']['latestUpdate'],
                time=datetime.now(),
            ))

    def index(self) -> pd.DataFrame:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.google_api_credential, scopes=SCOPES)
        http = credentials.authorize(httplib2.Http())

        service = build('indexing', 'v3', credentials=credentials)
        batch = service.new_batch_http_request(callback=self.api_callback)
        for url in urls:
            batch.add(service.urlNotifications().publish(body={"url": url, "type": 'URL_UPDATED'}))
        batch.execute()
        return pd.DataFrame(self.successful_urls)


def read_urls(path: str) -> List[str]:
    with open(path) as f:
        return f.readlines()


def main(args: argparse.Namespace):
    urls = read_urls(args.include)
    exclude_exists = os.path.isfile(args.exclude)
    if exclude_exists:
        exclude_urls = pd.read_csv(args.exclude)
        urls = sorted(set(urls) - set(exclude_urls['url'].tolist()))[:args.max_index]

    indexer = Indexer(urls, args.google_api_credential)
    successful_urls = indexer.index()
    if exclude_exists:
        exclude_urls = pd.concat([exclude_urls, successful_urls])
    else:
        exclude_urls = successful_urls
    exclude_urls.to_csv(args.exclude, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Index pages to google')
    parser.add_argument('--include', '-i', help='index this urls', required=True)
    parser.add_argument('--exclude', '-e', help='exclude this urls', required=True)
    parser.add_argument('--max-index', help='max number of urls to index', default=100, type=int)
    parser.add_argument('--google-api-credential', '-c', help='path to credential file', required=True)

    args = parser.parse_args()
    main(args)

