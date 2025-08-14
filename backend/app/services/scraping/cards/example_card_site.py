from typing import Iterable, Dict, Any
from bs4 import BeautifulSoup
from ..base import Scraper
from importlib import resources

class ExampleCardSiteScraper(Scraper):
    def scrape(self) -> Iterable[Dict[str, Any]]:
        # Load local HTML fixture bundled in package for deterministic output
        with resources.files(__package__).joinpath("fixtures/cards_sample.html").open("r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table#cards tbody tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.select("td")]
            if len(cols) < 5:
                continue
            yield {
                "name": cols[0],
                "issuer": cols[1],
                "network": cols[2] or None,
                "annual_fee": float(cols[3]) if cols[3] else None,
                "rewards": cols[4] or None,
                "country": cols[5] if len(cols) > 5 else None,
            }