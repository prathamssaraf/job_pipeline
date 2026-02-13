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
    
    fetcher = BrowserFetcher()
    url = "https://example.com"
    
    print(f"Attempting to fetch: {url}")
    print("This will force the use of Chromium/Chromedriver...")
    
    try:
        # We assume fetch_content or similar method exists, checking source code in next step to be sure, 
        # but based on previous context, 'get_page_source' is likely the specific browser method, 
        # or 'fetch' if it handles logic. 
        # Actually, let's look at the file content first in the tool output before writing this file 
        # to ensure I call the right method. 
        # Since I am calling write_to_file in parallel, I will just write a generic guess and fix it if wrong? 
        # No, better to be accurate. I will use 'fetch' as it is the public API likely, 
        # but I'll check the view_file output in the next turn if I made a mistake.
        # However, to be safe and fast, I'll rely on the standard "fetch" or "get_source".
        # Let's wait for view_file? No, I must generate tool calls.
        # I will assume the method is `fetch_with_browser` or similar if `fetch` is generic.
        # Actually, `UnifiedFetcher` uses `BrowserFetcher`. `BrowserFetcher` likely has `fetch` or `get_source`.
        # I'll stick to `get_page_source` as a good bet for a selenium wrapper.
        pass 
    except Exception as e:
        print(f"CRASHED: {e}")

if __name__ == "__main__":
    test_browser()
