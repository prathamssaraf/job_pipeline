import logging
import sys
import time
from browser_fetcher import BrowserFetcher

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_browser():
    print("="*50)
    print("TESTING BROWSER FETCHER ON TERMUX")
    print("="*50)
    
    # Initialize fetcher
    try:
        fetcher = BrowserFetcher()
    except Exception as e:
        print(f"FAILED to initialize BrowserFetcher: {e}")
        return

    # This URL previously crashed the browser
    url = "https://careers.salesforce.com/en/jobs/?search=&country=United+States+of+America&team=Software+Engineering&jobtype=New+Grads&pagesize=20#results"
    
    print(f"Attempting to fetch: {url}")
    print("This will force the use of Chromium/Chromedriver...")
    print("If this crashes, it's a driver/browser issue.")
    
    try:
        # fetch() returns the HTML string or None
        html = fetcher.fetch(url)
        
        if html:
            print("\n" + "="*50)
            print("SUCCESS! Browser fetched content.")
            print(f"Content length: {len(html)} chars")
            print("Head snippet:")
            print(html[:300])
            print("="*50)
        else:
            print("\n" + "="*50)
            print("FAILURE: Fetch returned None.")
            print("="*50)
            
    except Exception as e:
        print(f"\nCRASHED with error: {e}")

if __name__ == "__main__":
    test_browser()
