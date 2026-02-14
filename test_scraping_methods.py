import requests
import urllib.request
import subprocess
import os
import sys

# Targets
TARGETS = [
    ("Salesforce", "https://careers.salesforce.com/en/jobs/?search=&country=United+States+of+America&team=Software+Engineering&jobtype=New+Grads&pagesize=20#results"),
    ("Meta", "https://www.metacareers.com/jobsearch?teams[0]=University%20Grad%20-%20Business&teams[1]=University%20Grad%20-%20Engineering%2C%20Tech%20%26%20Design&teams[2]=University%20Grad%20-%20PhD%20%26%20Postdoc&sort_by_new=true&offices[0]=North%20America")
]

# SSL Fix for Termux
if os.path.exists("/data/data/com.termux/files/usr/etc/tls/cert.pem"):
    os.environ["SSL_CERT_FILE"] = "/data/data/com.termux/files/usr/etc/tls/cert.pem"

def log(msg):
    print(f"[TEST] {msg}")

def test_requests_desktop(url):
    log("Method: Requests (Desktop UA)")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return True, f"Success ({len(resp.text)} bytes)"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_requests_mobile(url):
    log("Method: Requests (Mobile UA)")
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return True, f"Success ({len(resp.text)} bytes)"
        return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_urllib(url):
    log("Method: urllib (Standard Lib)")
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
            return True, f"Success ({len(html)} bytes)"
    except Exception as e:
        return False, str(e)

def test_curl(url):
    log("Method: Curl (Subprocess)")
    # Basic curl mimicking a browser
    cmd = [
        "curl", "-L", "-s",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and len(result.stdout) > 500:
             return True, f"Success ({len(result.stdout)} bytes)"
        return False, f"Return Code {result.returncode} (Len: {len(result.stdout)})"
    except Exception as e:
        return False, str(e)

def main():
    print("=== STARTING SCRAPING TEST ===")
    for name, url in TARGETS:
        print(f"\nTarget: {name}")
        print(f"URL: {url}")
        print("-" * 30)
        
        methods = [
            test_requests_desktop,
            test_requests_mobile,
            test_urllib,
            test_curl
        ]
        
        for method in methods:
            success, msg = method(url)
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | {msg}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
