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
    
    try:
        # Enable verbose logging for debugging
        service_args = ["--verbose", "--log-path=/data/data/com.termux/files/home/job_pipeline/chromedriver.log"]
        fetcher = BrowserFetcher(service_args=service_args)
        
        print(f"DEBUG: Logging enabled at /data/data/com.termux/files/home/job_pipeline/chromedriver.log")
        
    except Exception as e:
        print(f"FAILED to initialize BrowserFetcher: {e}")
        return

    # Define test targets
    targets = [
        ("LIGHT", "https://example.com"),
        ("MEDIUM", "https://www.google.com"),
        ("HEAVY", "https://careers.salesforce.com/en/jobs/?search=&country=United+States+of+America&team=Software+Engineering&jobtype=New+Grads&pagesize=20#results")
    ]
    
    for name, url in targets:
        print(f"\n--- TESTING {name} ({url}) ---")
        try:
            html = fetcher.fetch(url)
            if html:
                print(f"SUCCESS: Fetched {len(html)} bytes.")
            else:
                print("FAILURE: Returned None.")
        except Exception as e:
            print(f"CRASHED on {name}: {e}")
            break # Stop on first crash

    # Print logs at the end if they exist
    log_path = "/data/data/com.termux/files/home/job_pipeline/chromedriver.log"
    if os.path.exists(log_path):
        print("\n" + "="*20 + " CHROMEDRIVER LOG (LAST 20 LINES) " + "="*20)
        try:
            with open(log_path, 'r', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.strip())
        except Exception as log_err:
            print(f"Could not read log file: {log_err}")
        print("="*60)
    else:
        print(f"\nLog file not found at: {log_path}")

if __name__ == "__main__":
    test_browser()
