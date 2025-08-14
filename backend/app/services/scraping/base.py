from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any
import requests
from bs4 import BeautifulSoup
from ..utils.http import get_session

class Scraper(ABC):
    @abstractmethod
    def scrape(self) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

class HtmlScraper(Scraper):
    def __init__(self, url: str) -> None:
        self.url = url
        self.session = get_session()

    def fetch(self) -> BeautifulSoup:
        response = self.session.get(self.url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")