import subprocess
import time
import sys
import urllib.request
import os
from playwright.sync_api import sync_playwright

def capture():
    os.makedirs("video_frames/raw_screens", exist_ok=True)
    
    proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8508", "--server.headless", "true"
    ])

    for i in range(25):
        time.sleep(1)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8508/_stcore/health")
            if resp.status == 200:
                break
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto("http://127.0.0.1:8508", timeout=30000)
            
            # Wait for Priority Action Queue to appear
            print("Waiting for page compute...")
            page.wait_for_selector('text=Priority Action Queue', timeout=60000)
            time.sleep(2)
            
            # 1. Main Deal Desk overview
            page.screenshot(path="video_frames/raw_screens/screen_deal_desk.png")
            print("Captured screen_deal_desk.png")
            
            # 2. Click tab by text
            tab = page.locator('button:has-text("Live Benchmark")')
            if tab.count() > 0:
                tab.first.click()
                time.sleep(3)
                page.screenshot(path="video_frames/raw_screens/screen_benchmark.png")
                print("Captured screen_benchmark.png successfully!")

            browser.close()
            return True
    finally:
        proc.terminate()
        print("Streamlit terminated")

if __name__ == "__main__":
    capture()
