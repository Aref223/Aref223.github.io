"""
Scraping utilities for web scraping operations.

This module provides comprehensive web scraping functionality for extracting
card information from various sources with proper error handling and rate limiting.
"""

import time
import random
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from fake_useragent import UserAgent
import re

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedCardData:
    """Data class for scraped card information."""
    card_number: str
    expiry_date: Optional[str] = None
    cvv: Optional[str] = None
    cardholder_name: Optional[str] = None
    card_type: Optional[str] = None
    bank_name: Optional[str] = None
    source_url: Optional[str] = None
    confidence_score: float = 0.0
    extraction_method: str = "unknown"


class ScrapingEngine(ABC):
    """
    Abstract base class for scraping engines.
    
    This class defines the interface for different scraping engines
    and provides common functionality for web scraping operations.
    """
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3):
        """
        Initialize scraping engine.
        
        Args:
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.session = requests.Session()
        self.ua = UserAgent()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup session with proper headers and configuration."""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(1.0, 3.0)
    
    def _make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if failed
        """
        for attempt in range(self.retry_attempts):
            try:
                # Add random delay
                time.sleep(self._get_random_delay())
                
                # Update user agent
                self.session.headers['User-Agent'] = self.ua.random
                
                # Make request
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.retry_attempts - 1:
                    logger.error(f"All request attempts failed for {url}")
                    return None
                
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return None
    
    def _extract_card_patterns(self, text: str) -> List[str]:
        """
        Extract potential card numbers from text using regex patterns.
        
        Args:
            text: Text to search for card numbers
            
        Returns:
            List of potential card numbers
        """
        # Remove common separators
        text = re.sub(r'[\s\-]', '', text)
        
        # Card number patterns (13-19 digits)
        patterns = [
            r'\b\d{13,19}\b',  # Standard card numbers
            r'\b4\d{12,15}\b',  # Visa cards
            r'\b5[1-5]\d{14}\b',  # Mastercard
            r'\b3[47]\d{13}\b',  # American Express
        ]
        
        card_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            card_numbers.extend(matches)
        
        return list(set(card_numbers))  # Remove duplicates
    
    def _extract_expiry_patterns(self, text: str) -> List[str]:
        """
        Extract expiry dates from text.
        
        Args:
            text: Text to search for expiry dates
            
        Returns:
            List of potential expiry dates
        """
        # Expiry date patterns
        patterns = [
            r'\b(0[1-9]|1[0-2])/([0-9]{2})\b',  # MM/YY
            r'\b(0[1-9]|1[0-2])/([0-9]{4})\b',  # MM/YYYY
            r'\b(0[1-9]|1[0-2])-([0-9]{2})\b',  # MM-YY
            r'\b(0[1-9]|1[0-2])-([0-9]{4})\b',  # MM-YYYY
        ]
        
        expiry_dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    expiry_dates.append(f"{match[0]}/{match[1]}")
        
        return list(set(expiry_dates))
    
    def _extract_cvv_patterns(self, text: str) -> List[str]:
        """
        Extract CVV codes from text.
        
        Args:
            text: Text to search for CVV codes
            
        Returns:
            List of potential CVV codes
        """
        # CVV patterns
        patterns = [
            r'\b\d{3}\b',  # 3-digit CVV
            r'\b\d{4}\b',  # 4-digit CVV (Amex)
        ]
        
        cvv_codes = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            cvv_codes.extend(matches)
        
        return list(set(cvv_codes))
    
    @abstractmethod
    def scrape_url(self, url: str) -> List[ScrapedCardData]:
        """
        Scrape card data from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            List of scraped card data
        """
        pass


class RequestsScrapingEngine(ScrapingEngine):
    """
    Scraping engine using requests library.
    
    This engine uses the requests library for simple HTTP requests
    and BeautifulSoup for HTML parsing.
    """
    
    def scrape_url(self, url: str) -> List[ScrapedCardData]:
        """
        Scrape card data from URL using requests.
        
        Args:
            url: URL to scrape
            
        Returns:
            List of scraped card data
        """
        try:
            # Make request
            response = self._make_request(url)
            if not response:
                return []
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text()
            
            # Extract card data
            return self._extract_card_data_from_text(text_content, url)
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return []
    
    def _extract_card_data_from_text(self, text: str, source_url: str) -> List[ScrapedCardData]:
        """
        Extract card data from text content.
        
        Args:
            text: Text content to analyze
            source_url: Source URL
            
        Returns:
            List of scraped card data
        """
        card_data_list = []
        
        # Extract card numbers
        card_numbers = self._extract_card_patterns(text)
        
        for card_number in card_numbers:
            # Extract associated data
            expiry_dates = self._extract_expiry_patterns(text)
            cvv_codes = self._extract_cvv_patterns(text)
            
            # Create card data object
            card_data = ScrapedCardData(
                card_number=card_number,
                expiry_date=expiry_dates[0] if expiry_dates else None,
                cvv=cvv_codes[0] if cvv_codes else None,
                source_url=source_url,
                confidence_score=0.5  # Basic confidence for text extraction
            )
            
            card_data_list.append(card_data)
        
        return card_data_list


class SeleniumScrapingEngine(ScrapingEngine):
    """
    Scraping engine using Selenium WebDriver.
    
    This engine uses Selenium for JavaScript-heavy websites
    and dynamic content extraction.
    """
    
    def __init__(self, headless: bool = True, **kwargs):
        """
        Initialize Selenium scraping engine.
        
        Args:
            headless: Whether to run browser in headless mode
            **kwargs: Additional arguments
        """
        super().__init__(**kwargs)
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self) -> None:
        """Setup Chrome WebDriver with proper options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.ua.random}")
        
        # Disable images and CSS for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
        except WebDriverException as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def scrape_url(self, url: str) -> List[ScrapedCardData]:
        """
        Scrape card data from URL using Selenium.
        
        Args:
            url: URL to scrape
            
        Returns:
            List of scraped card data
        """
        try:
            if not self.driver:
                self._setup_driver()
            
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source
            page_source = self.driver.page_source
            
            # Extract card data
            return self._extract_card_data_from_text(page_source, url)
            
        except TimeoutException:
            logger.warning(f"Timeout loading page: {url}")
            return []
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return []
    
    def _extract_card_data_from_text(self, text: str, source_url: str) -> List[ScrapedCardData]:
        """
        Extract card data from text content (same as requests engine).
        
        Args:
            text: Text content to analyze
            source_url: Source URL
            
        Returns:
            List of scraped card data
        """
        card_data_list = []
        
        # Extract card numbers
        card_numbers = self._extract_card_patterns(text)
        
        for card_number in card_numbers:
            # Extract associated data
            expiry_dates = self._extract_expiry_patterns(text)
            cvv_codes = self._extract_cvv_patterns(text)
            
            # Create card data object
            card_data = ScrapedCardData(
                card_number=card_number,
                expiry_date=expiry_dates[0] if expiry_dates else None,
                cvv=cvv_codes[0] if cvv_codes else None,
                source_url=source_url,
                confidence_score=0.7  # Higher confidence for Selenium
            )
            
            card_data_list.append(card_data)
        
        return card_data_list
    
    def close(self) -> None:
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None


class VisaScraper:
    """
    Specialized scraper for Visa card information.
    
    This scraper is specifically designed to extract Visa card data
    from various sources with enhanced validation and detection.
    """
    
    def __init__(self, engine_type: str = "selenium"):
        """
        Initialize Visa scraper.
        
        Args:
            engine_type: Type of scraping engine ("requests" or "selenium")
        """
        if engine_type == "selenium":
            self.engine = SeleniumScrapingEngine()
        else:
            self.engine = RequestsScrapingEngine()
    
    def scrape_visa_cards(self, urls: List[str]) -> List[ScrapedCardData]:
        """
        Scrape Visa cards from multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped Visa card data
        """
        all_cards = []
        
        for url in urls:
            try:
                cards = self.engine.scrape_url(url)
                
                # Filter for Visa cards only
                visa_cards = [
                    card for card in cards
                    if card.card_number.startswith("4") and len(card.card_number) in [13, 16, 19]
                ]
                
                # Enhance Visa card data
                for card in visa_cards:
                    card.card_type = "visa"
                    card.confidence_score += 0.2  # Bonus for Visa detection
                
                all_cards.extend(visa_cards)
                
            except Exception as e:
                logger.error(f"Error scraping Visa cards from {url}: {e}")
        
        return all_cards


class DebitCardScraper:
    """
    Specialized scraper for debit card information.
    
    This scraper is specifically designed to extract debit card data
    from various sources with enhanced validation and detection.
    """
    
    def __init__(self, engine_type: str = "selenium"):
        """
        Initialize debit card scraper.
        
        Args:
            engine_type: Type of scraping engine ("requests" or "selenium")
        """
        if engine_type == "selenium":
            self.engine = SeleniumScrapingEngine()
        else:
            self.engine = RequestsScrapingEngine()
    
    def scrape_debit_cards(self, urls: List[str]) -> List[ScrapedCardData]:
        """
        Scrape debit cards from multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped debit card data
        """
        all_cards = []
        
        for url in urls:
            try:
                cards = self.engine.scrape_url(url)
                
                # Filter for debit cards (typically 16 digits)
                debit_cards = [
                    card for card in cards
                    if len(card.card_number) == 16
                ]
                
                # Enhance debit card data
                for card in debit_cards:
                    card.card_type = "debit"
                    card.confidence_score += 0.1  # Bonus for debit detection
                
                all_cards.extend(debit_cards)
                
            except Exception as e:
                logger.error(f"Error scraping debit cards from {url}: {e}")
        
        return all_cards


class ScrapingManager:
    """
    High-level scraping manager for coordinating scraping operations.
    
    This class provides a unified interface for different types of scraping
    operations with proper resource management and error handling.
    """
    
    def __init__(self):
        """Initialize scraping manager."""
        self.visa_scraper = VisaScraper()
        self.debit_scraper = DebitCardScraper()
        self.active_drivers = []
    
    def scrape_cards(self, urls: List[str], card_types: List[str] = None) -> List[ScrapedCardData]:
        """
        Scrape cards from URLs based on specified types.
        
        Args:
            urls: List of URLs to scrape
            card_types: List of card types to scrape (visa, debit, etc.)
            
        Returns:
            List of scraped card data
        """
        if card_types is None:
            card_types = ["visa", "debit"]
        
        all_cards = []
        
        try:
            for card_type in card_types:
                if card_type.lower() == "visa":
                    cards = self.visa_scraper.scrape_visa_cards(urls)
                    all_cards.extend(cards)
                elif card_type.lower() == "debit":
                    cards = self.debit_scraper.scrape_debit_cards(urls)
                    all_cards.extend(cards)
            
            # Remove duplicates based on card number
            unique_cards = {}
            for card in all_cards:
                if card.card_number not in unique_cards:
                    unique_cards[card.card_number] = card
                else:
                    # Keep the one with higher confidence
                    if card.confidence_score > unique_cards[card.card_number].confidence_score:
                        unique_cards[card.card_number] = card
            
            return list(unique_cards.values())
            
        except Exception as e:
            logger.error(f"Error in scraping manager: {e}")
            return []
    
    def close(self) -> None:
        """Close all active drivers and cleanup resources."""
        try:
            if hasattr(self.visa_scraper.engine, 'close'):
                self.visa_scraper.engine.close()
            if hasattr(self.debit_scraper.engine, 'close'):
                self.debit_scraper.engine.close()
        except Exception as e:
            logger.error(f"Error closing scraping manager: {e}")