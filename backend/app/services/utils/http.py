import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ...config import settings

_session: requests.Session | None = None


def get_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session
    session = requests.Session()
    session.headers.update({"User-Agent": settings.SCRAPER_USER_AGENT})
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    _session = session
    return session