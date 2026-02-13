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
    
    def __init__(self, timeout: int = 30, wait_for_content: int = 5, service_args: Optional[list] = None):
        """
        Args:
            timeout: Page load timeout in seconds
            wait_for_content: Extra time to wait for JS content to load
            service_args: Optional list of args for chromedriver service
        """
        self.timeout = timeout
        self.wait_for_content = wait_for_content
        self.service_args = service_args or []
    
    def _get_driver(self):
        """Create headless Chrome driver."""
        options = Options()
        options.add_argument("--headless") # Revert to legacy headless (lighter?)
        options.add_argument("--no-sandbox")
        
        # Aggressive memory saving
        options.add_argument("--disk-cache-size=1") 
        options.add_argument("--media-cache-size=1")
        
        # Standard linux flags
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=800,600") # Smaller window = less RAM
        options.page_load_strategy = 'none' # STOP loading as soon as connection is made (prevents rendering crashes)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Check if running in Termux (Android)
        if hasattr(os, 'environ') and 'PREFIX' in os.environ and 'com.termux' in os.environ.get('PREFIX', ''):
            logger.info("Termux environment detected. Using system chromedriver.")
            
            # CRITICAL FIX: Kill DBus attempts which cause crashes/hangs
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = '/dev/null'
            
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
            options.add_argument("--disable-accelerated-2d-canvas")
            options.add_argument("--enable-features=NetworkServiceInProcess")
            options.add_argument("--blink-settings=imagesEnabled=false") # Save memory
            
            # NUCLEAR OPTION: OTA (Over The Air) & Background updates disabled
            options.add_argument("--disable-breakpad")
            options.add_argument("--disable-client-side-phishing-detection")
            options.add_argument("--disable-component-extensions-with-background-pages")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-networking")
            
            # CRITICAL MEMORY SAVERS: Disable Site Isolation (huge RAM saver)
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            
            # Use Mobile User Agent to get lighter pages
            mobile_ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
            options.add_argument(f"user-agent={mobile_ua}")
            # Note: --single-process removed as it causes instability on some pages
            
            # Explicitly find chromedriver path
            chromedriver_path = shutil.which("chromedriver") or "/data/data/com.termux/files/usr/bin/chromedriver"
            logger.info(f"Termux: Using chromedriver at {chromedriver_path}")
            
            if not os.path.exists(chromedriver_path):
                logger.error(f"Chromedriver NOT FOUND at {chromedriver_path}")
            
            service = Service(executable_path=chromedriver_path, service_args=self.service_args)
        else:
            # Standard desktop environment
            # Auto-download and manage chromedriver
            service = Service(ChromeDriverManager().install(), service_args=self.service_args)
            
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
            # Navigation
            driver.get(url)
            
            # Wait for content
            time.sleep(self.wait_for_content)
            
            # CRITICAL: On Termux, avoid complex interactions/scrolling as they crash the renderer
            is_termux = False
            try:
                if "/com.termux/" in driver.service.path or os.path.exists("/data/data/com.termux"):
                     is_termux = True
            except:
                pass

            if not is_termux:
                # Scroll to bottom to trigger lazy loading (Desktop only)
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Could not scroll: {e}")
            else:
                logger.info("Termux detected: Skipping scroll/JS to prevent crash.")
                time.sleep(2) # Just wait a bit for eager load
            
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
