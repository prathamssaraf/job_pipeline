import logging
import sys
import time
import os
import requests
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
        ("HEAVY", "https://www.metacareers.com/jobsearch?teams[0]=University%20Grad%20-%20Business&teams[1]=University%20Grad%20-%20Engineering%2C%20Tech%20%26%20Design&teams[2]=University%20Grad%20-%20PhD%20%26%20Postdoc&sort_by_new=true&offices[0]=North%20America")
    ]
    
    for name, url in targets:
        print(f"\n--- TESTING {name} ({url}) ---")
        
        # 1. Test Browser
        print("[BROWSER] Attempting fetch...")
        try:
            html = fetcher.fetch(url)
            if html:
                print(f"[BROWSER] SUCCESS: Fetched {len(html)} bytes.")
            else:
                print("[BROWSER] FAILURE: Returned None.")
        except Exception as e:
            print(f"[BROWSER] CRASHED: {e}")

        # 2. Test HTTP Fallback (simulating UnifiedFetcher)
        print("[HTTP]    Attempting fetch (Fallback)...")
        try:
            # Better headers to avoid 400 Bad Request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Temporary SSL Verification fix for Termux
            verify_ssl = True
            if os.path.exists("/data/data/com.termux/files/usr/etc/tls/cert.pem"):
                os.environ["SSL_CERT_FILE"] = "/data/data/com.termux/files/usr/etc/tls/cert.pem"
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                 print(f"[HTTP]    SUCCESS: Fetched {len(response.text)} bytes.")
            else:
                 print(f"[HTTP]    FAILURE: Status Code {response.status_code}")
                 print(f"[HTTP]    Response headers: {response.headers}")
        except Exception as e:
            print(f"[HTTP]    FAILED: {e}")

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
