"""Capture high-definition live application screenshots with Playwright Chrome."""

import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "temp_video_build" / "live_screens"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8599
URL = f"http://localhost:{PORT}"

def main():
    print("=" * 60)
    print("CAPTURING ALL LIVE HIGH-RES APP SCREENS FOR VIDEO")
    print("=" * 60)

    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT), "--server.headless", "true"],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(6)
        print("[1/3] Connecting with Playwright Chrome at 1920x1080...")

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)

            print(f"  - Navigating to {URL}...")
            page.goto(URL, timeout=60000)
            print("  - Waiting for dashboard metrics to render...")
            page.wait_for_selector("text=CONFIRMED CASH DISCREPANCIES", timeout=60000)
            time.sleep(6)

            # Screen 1: Deal Desk Live with ORD-LEAK-4348 ($1,255.00) at #1
            s1_path = str(OUTPUT_DIR / "01_deal_desk_live.png")
            page.screenshot(path=s1_path, full_page=False)
            print(f"  [SAVED] {s1_path}")

            # Screen 2: Scroll Right Inspector down to show Evidence + Grounded Draft
            print("  - Scrolling right inspector to show Evidence and Grounded Action Notice...")
            page.evaluate("() => { const el = document.querySelector('.stMain') || document.documentElement; el.scrollTop = 380; }")
            time.sleep(2)
            s2_path = str(OUTPUT_DIR / "02_evidence_and_action.png")
            page.screenshot(path=s2_path, full_page=False)
            print(f"  [SAVED] {s2_path}")

            # Reset scroll
            page.evaluate("() => { const el = document.querySelector('.stMain') || document.documentElement; el.scrollTop = 0; }")
            time.sleep(1)

            # Screen 3: Switch Objective to Prevent Stockouts & All Ranked Items
            print("  - Switching Optimization Goal to 'Prevent Stockouts'...")
            page.locator("label:has-text('Prevent Stockouts')").click()
            time.sleep(3)

            print("  - Clicking 'All Ranked Items'...")
            try:
                page.get_by_text("All Ranked Items").click()
            except Exception as e:
                print("    get_by_text error:", e)
            time.sleep(3)

            s3_path = str(OUTPUT_DIR / "03_stockout_promoted.png")
            page.screenshot(path=s3_path, full_page=False)
            print(f"  [SAVED] {s3_path}")

            # Screen 4: Switch to Tab 2 (Live Benchmark & Confusion Matrix)
            print("  - Navigating to Tab 2 (Live Benchmark & Confusion Matrix)...")
            tabs = page.locator("button[role='tab']").all()
            if len(tabs) >= 2:
                tabs[1].click()
                time.sleep(4)

            s4_path = str(OUTPUT_DIR / "04_amd_benchmark_scaling.png")
            page.screenshot(path=s4_path, full_page=False)
            print(f"  [SAVED] {s4_path}")

            # Screen 5: Scroll down in Tab 2 to show Stress Confusion Matrix
            print("  - Scrolling down in Tab 2 to show Stress Confusion Matrix...")
            page.evaluate("() => { const el = document.querySelector('.stMain') || document.documentElement; el.scrollTop = 700; }")
            time.sleep(2)
            s5_path = str(OUTPUT_DIR / "05_stress_confusion_matrix.png")
            page.screenshot(path=s5_path, full_page=False)
            print(f"  [SAVED] {s5_path}")

            browser.close()

    finally:
        print("[2/3] Terminating Streamlit server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    print("[3/3] Screenshot capture complete!")

if __name__ == "__main__":
    main()
