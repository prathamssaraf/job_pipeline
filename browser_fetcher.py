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

import os
import shutil


from logger import get_logger

logger = get_logger(__name__)


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
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Check if running in Termux (Android)
        if hasattr(os, 'environ') and 'PREFIX' in os.environ and 'com.termux' in os.environ.get('PREFIX', ''):
            logger.info("Termux environment detected. Using system chromedriver.")
            # In Termux, we must use the system-installed chromedriver
            # pkg install chromium chromedriver
            options.binary_location = "/data/data/com.termux/files/usr/bin/chromium-browser"
            
            # Specific flags for Termux/Android
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")
            # Memory saving flags - CRITICAL for Termux
            options.add_argument("--disable-features=site-per-process")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-breakpad")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-cloud-import")
            options.add_argument("--disable-gpu-compositing")
            
            # Use Mobile User Agent to get lighter pages
            mobile_ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
            options.add_argument(f"user-agent={mobile_ua}")
            # Note: --single-process removed as it causes instability on some pages
            
            # Explicitly find chromedriver path
            chromedriver_path = shutil.which("chromedriver") or "/data/data/com.termux/files/usr/bin/chromedriver"
            logger.info(f"Termux: Using chromedriver at {chromedriver_path}")
            
            if not os.path.exists(chromedriver_path):
                logger.error(f"Chromedriver NOT FOUND at {chromedriver_path}")
            
            service = Service(executable_path=chromedriver_path)
        else:
            # Standard desktop environment
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
            logger.error("Selenium not installed. Run: pip install selenium webdriver-manager")
            return None
        
        driver = None
        try:
            logger.debug(f"Loading {url} with headless browser...")
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
            
            logger.info(f"Fetched {len(html)} bytes from {url}")
            return html
            
        except TimeoutException:
            logger.error(f"Timeout loading {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
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
