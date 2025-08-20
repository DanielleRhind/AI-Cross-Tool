# backend/cross_algo.py


import requests
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
import ast , re
import json
from playwright.sync_api import sync_playwright
import os
from chat_with_ollama import chat
from boost import algorithm_boost , algorithm_buck , algorithm_buck_boost
# from boost import boost



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


def pdf_to_text(partnumber):
# Open the PDF file
    pdf_path = f"./downloads/{partnumber}.pdf"
    doc = fitz.open(pdf_path)

    # Extract text from all pages into one string
    all_text = ""
    # page = doc[0]
    for page in doc[:2]:
        all_text += page.get_text("text")

    # Optional: close the document
    doc.close()

    # Print or use the full extracted text
    # print(all_text)  # Show first 1000 characters
    # print(type(all_text))


    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(all_text)


import numpy as np


def format_dimensions(s):
    # Find all numbers with optional decimals
    numbers = re.findall(r"\d+\.\d+|\d+", s)
    # Convert to float and back to string to remove unnecessary trailing zeros
    cleaned_numbers = [str(float(num)) for num in numbers]
    # Join with 'x'
    return "x".join(cleaned_numbers)


def algorithm_main(response:str ,
              boolean_package : str,
              tol :float = 0.8,
              top_n :int = 10,
              min_freq_overlap_ratio :float = 0.1
              ):
    
    import re, json

    # 1) Grab the first [...] block
    m = re.search(r'\[.*\]', response, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON array foundn response!")
    array_text = m.group(0)
    # print("array_text:", array_text)
    # 2) Now parse it
    values = json.loads(array_text)

    if not values:
        print("⚠️  No matches found – nothing to compare.")
        # You can return, raise a custom exception, or set a default outcome
    
    match values[0]:
        case "buck":
            result = algorithm_buck(response,boolean_package,tol,top_n,min_freq_overlap_ratio)
        case "boost":
            result = algorithm_boost(response,boolean_package,tol,top_n,min_freq_overlap_ratio)
        case "buck-boost":
            result = algorithm_buck_boost(response,boolean_package,tol,top_n,min_freq_overlap_ratio)
    print(type(result))
    return result


