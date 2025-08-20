# backend/selenium_helper.py

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def selenium(partnumber):
    PART      = partnumber
    DOWNLOADS = os.path.abspath("downloads")
    os.makedirs(DOWNLOADS, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        # 1) Go to TI Power Management overview
        page.goto("https://www.ti.com/power-management/overview.html")

        # 2) Search for the part
        page.fill('input[part="input"]', PART)
        page.click('button[part="submit-button"]')
        page.wait_for_load_state("networkidle")

        # 3) Click the exact part link
        page.click(f'text="{PART}"')
        page.wait_for_load_state("networkidle")

        # 4) Grab the PDF anchor href
        link = page.locator('a[data-navtitle="data sheet-pdf"]')
        href = link.get_attribute("href")
        if not href:
            raise RuntimeError("Could not find PDF link href")

        # TI serves that as a relative URL like "/lit/pdf/tps628501"
        pdf_url = "https://www.ti.com" + href

        # 5) Fetch it directly via Playwright’s request context
        response = page.request.get(pdf_url)
        if response.status != 200:
            raise RuntimeError(f"Failed to download PDF, status {response.status}")

        pdf_bytes = response.body()

        # 6) Write to disk
        out_path = os.path.join(DOWNLOADS, f"{PART}.pdf")
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)

        print("✅ Saved PDF to", out_path)
        browser.close()



