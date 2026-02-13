"""
HTML Fetcher module for Job Pipeline Tracker.
Fetches job pages with proper headers and retry logic.
"""

import time
import requests
from typing import Optional
from logger import get_logger

logger = get_logger(__name__)


class Fetcher:
    """Fetches HTML content from job pages."""
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, delay_between_requests: float = 2.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
    
    def fetch(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string, or None if fetch failed
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # Rate limiting - be nice to servers
                time.sleep(self.delay)
                
                return response.text
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * self.delay
                    logger.debug(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def fetch_multiple(self, urls: list[str]) -> dict[str, Optional[str]]:
        """
        Fetch HTML from multiple URLs.
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            Dictionary mapping URL to HTML content (or None if failed)
        """
        results = {}
        for url in urls:
            results[url] = self.fetch(url)
        return results


# Default fetcher instance
fetcher = Fetcher()
