"""
Unified Fetcher with Smart Routing and Fallback.
Routes between browser and HTTP fetching based on source configuration.
"""

from typing import Optional
from dataclasses import dataclass

from fetcher import fetcher
from browser_fetcher import browser_fetcher, SELENIUM_AVAILABLE
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class JobSource:
    """Represents a job source with fetch configuration."""
    url: str
    name: str = ""
    requires_browser: bool = False
    
    def __post_init__(self):
        if not self.name:
            # Extract domain as name if not provided
            from urllib.parse import urlparse
            self.name = urlparse(self.url).netloc


class UnifiedFetcher:
    """
    Smart fetcher that routes between browser and HTTP based on config.
    Includes automatic fallback for resilience.
    """
    
    def __init__(self, enable_fallback: bool = True):
        """
        Args:
            enable_fallback: If True, falls back to HTTP when browser fails
        """
        self.enable_fallback = enable_fallback
    
    def fetch(self, url: str, requires_browser: bool = False) -> Optional[str]:
        """
        Fetch HTML from a URL using the appropriate method.
        
        Args:
            url: The URL to fetch
            requires_browser: If True, uses headless browser (with HTTP fallback)
            
        Returns:
            HTML content or None if all methods failed
        """
        html = None
        method_used = None
        
        if requires_browser and SELENIUM_AVAILABLE:
            # Try browser first for JS-heavy sites
            logger.info(f"Using browser for: {url}")
            html = browser_fetcher.fetch(url)
            method_used = "browser"
            
            # Fallback to HTTP if browser fails
            if not html and self.enable_fallback:
                logger.warning(f"Browser failed, falling back to HTTP: {url}")
                html = fetcher.fetch(url)
                method_used = "http (fallback)"
        else:
            # Use fast HTTP fetch for static sites
            if requires_browser and not SELENIUM_AVAILABLE:
                logger.warning(f"Selenium not available, using HTTP: {url}")
            else:
                logger.debug(f"Using HTTP for: {url}")
            html = fetcher.fetch(url)
            method_used = "http"
        
        if html:
            logger.info(f"Success ({method_used}): {len(html)} bytes from {url}")
        else:
            logger.error(f"Failed to fetch: {url}")
        
        return html
    
    def fetch_from_source(self, source: JobSource) -> Optional[str]:
        """Fetch HTML from a JobSource object."""
        return self.fetch(source.url, source.requires_browser)
    
    def fetch_multiple(self, sources: list[JobSource]) -> dict[str, Optional[str]]:
        """
        Fetch HTML from multiple job sources.
        
        Args:
            sources: List of JobSource objects
            
        Returns:
            Dictionary mapping URL to HTML content (or None if failed)
        """
        results = {}
        for source in sources:
            results[source.url] = self.fetch_from_source(source)
        return results
    
    def fetch_urls(self, urls: list[str], default_browser: bool = False) -> dict[str, Optional[str]]:
        """
        Fetch multiple URLs with a default browser setting.
        For backwards compatibility.
        
        Args:
            urls: List of URLs to fetch
            default_browser: Default requires_browser setting for all URLs
            
        Returns:
            Dictionary mapping URL to HTML content
        """
        results = {}
        for url in urls:
            results[url] = self.fetch(url, requires_browser=default_browser)
        return results


# Default unified fetcher instance
unified_fetcher = UnifiedFetcher()
