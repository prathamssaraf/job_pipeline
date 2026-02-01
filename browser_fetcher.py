"""
Browser-based HTML Fetcher using Selenium (headless).
For sites that require JavaScript execution like Meta Careers.
"""

import time
from typing import Optional

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class BrowserFetcher:
    """Fetches HTML from pages using headless Selenium."""
    
    def __init__(self, timeout: int = 30, wait_for_content: int = 5):
        """
        Args:
            timeout: Page load timeout in seconds
            wait_for_content: Extra time to wait for JS content to load
        """
        self.timeout = timeout
        self.wait_for_content = wait_for_content
    
    def _get_driver(self):
        """Create headless Chrome driver."""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Auto-download and manage chromedriver
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def fetch(self, url: str) -> Optional[str]:
        """
        Fetch HTML from a URL using headless Chrome.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Full HTML content after JavaScript execution, or None if failed
        """
        if not SELENIUM_AVAILABLE:
            print("[BrowserFetcher] Selenium not installed. Run: pip install selenium webdriver-manager")
            return None
        
        driver = None
        try:
            print(f"[BrowserFetcher] Loading {url}...")
            driver = self._get_driver()
            driver.set_page_load_timeout(self.timeout)
            
            # Navigate to page
            driver.get(url)
            
            # Wait for dynamic content to load
            time.sleep(self.wait_for_content)
            
            # Scroll to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Get full HTML
            html = driver.page_source
            
            print(f"[BrowserFetcher] Fetched {len(html)} bytes from {url}")
            return html
            
        except TimeoutException:
            print(f"[BrowserFetcher] Timeout loading {url}")
            return None
        except Exception as e:
            print(f"[BrowserFetcher] Error fetching {url}: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def fetch_multiple(self, urls: list[str]) -> dict[str, Optional[str]]:
        """Fetch HTML from multiple URLs."""
        results = {}
        for url in urls:
            results[url] = self.fetch(url)
        return results


# Default browser fetcher instance
browser_fetcher = BrowserFetcher()
