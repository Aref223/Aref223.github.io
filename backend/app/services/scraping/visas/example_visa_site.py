from typing import Iterable, Dict, Any
from bs4 import BeautifulSoup
from ..base import Scraper
from importlib import resources

class ExampleVisaSiteScraper(Scraper):
    def scrape(self) -> Iterable[Dict[str, Any]]:
        with resources.files(__package__).joinpath("fixtures/visas_sample.html").open("r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table#visas tbody tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.select("td")]
            if len(cols) < 3:
                continue
            yield {
                "from_country": cols[0],
                "to_country": cols[1],
                "requirement": cols[2],
                "source": "example_fixture",
            }