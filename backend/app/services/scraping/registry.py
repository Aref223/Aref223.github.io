from typing import Iterable, Dict, Any, List
from .cards.example_card_site import ExampleCardSiteScraper
from .visas.example_visa_site import ExampleVisaSiteScraper


def get_card_scrapers() -> List:
    return [ExampleCardSiteScraper()]


def get_visa_scrapers() -> List:
    return [ExampleVisaSiteScraper()]