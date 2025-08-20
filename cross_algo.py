import requests
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
import ast , re
import json
from playwright.sync_api import sync_playwright
import os
# from chat_with_ollama import chat
# ----------  Chat with Ollama ----------
def chat(prompt: str, *, model: str = "llama3") -> str:
    """
    Ask the local Ollama model *model* the *prompt* and return its text answer.
    """
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{host}/api/chat"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    return resp.json()["content"]


# def selenium_ADI(partnumber):
#     PART      = partnumber
#     DOWNLOADS = os.path.abspath("downloads")
#     os.makedirs(DOWNLOADS, exist_ok=True)
 
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False)
#         page    = browser.new_page()
 
#         # 1) Go to ADI Power Management overview
#         page.goto("https://www.analog.com/en/index.html")
 
#         # 2) Search for the part

#         # 2) Click the Search Open Button   
#         page.click("button[aria-label='Search'] , button')
#         # 2) Fill in the search bar with the part number and click Search
#         page.fill('input[class="aa-Input"]', PART)
#         page.click('button[class*="search-button"]')
#         page.wait_for_load_state("networkidle")
#         # 3) Click the exact part link
#         page.click(f'text="{PART}"')
#         page.wait_for_load_state("networkidle")
 
#         # 4) Grab the PDF anchor href
#         link = page.locator('a[href*="' + PART + '"]')
#         href = link.get_attribute("href")
#         if not href:
#             raise RuntimeError("Could not find PDF link href")
 
#         # TI serves that as a relative URL like "/lit/pdf/tps628501"
#         pdf_url = href
 
#         # 5) Fetch it directly via Playwright’s request context
#         response = page.request.get(pdf_url)
#         if response.status != 200:
#             raise RuntimeError(f"Failed to download PDF, status {response.status}")
 
#         pdf_bytes = response.body()
 
#         # 6) Write to disk
#         out_path = os.path.join(DOWNLOADS, f"{PART}.pdf")
#         with open(out_path, "wb") as f:
#             f.write(pdf_bytes)
 
#         print("✅ Saved PDF to", out_path)
#         browser.close()
    
def selenium_TI(partnumber):
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
 
 
def frequency_overlap_ratio(min1, max1, min2, max2):
    """
    Calculate symmetric fractional overlap between two frequency ranges.
    Returns 0 (no overlap) to 1 (shortest range fully overlapped).
    Symmetric means overlap(A,B) == overlap(B,A).
    """
    overlap_min = max(min1, min2)
    overlap_max = min(max1, max2)
    overlap_length = max(0, overlap_max - overlap_min)  # clamp to 0 if no overlap
 
    range1_length = max1 - min1
    range2_length = max2 - min2
 
    if range1_length <= 0 or range2_length <= 0:
        return 0  # invalid ranges
 
    shortest_range = min(range1_length, range2_length)  # symmetric normalization
    return overlap_length / shortest_range
 
 
def format_dimensions(s):
    # Find all numbers with optional decimals
    numbers = re.findall(r"\d+\.\d+|\d+", s)
    # Convert to float and back to string to remove unnecessary trailing zeros
    cleaned_numbers = [str(float(num)) for num in numbers]
    # Join with 'x'
    return "x".join(cleaned_numbers)
 
 
def algorithm_main(response:str ,
              boolean_package : str,
              tol :float = 1.2,
              top_n :int = 10,
              min_freq_overlap_ratio :float = 0.2
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
 
    # 3) Zip into your dict
    keys = ["Vin_min","Vin_max","Iout", "Freq_min", "Freq_max","Package", "Width" , "Length","Topology"]
    part_specs = dict(zip(keys, values))
 
    # part_specs['Package Size'] = format_dimensions(part_specs['Package Size'])    #competitor part specs
   
    print(part_specs)
    # print("done")
    # 2. Load dataset
    df = pd.read_excel('MPS_database.xlsx')
 
    # print(df.dtypes)
    print("done")
 
    comp_spec = part_specs
 
 
    print("range in here")
    mask = (
        (np.abs(df['Vin_min'] - comp_spec['Vin_min']) <= tol * comp_spec['Vin_min']) &
        (np.abs(df['Vin_max'] - comp_spec['Vin_max']) <= tol * comp_spec['Vin_max']) &
        (np.abs(df['Iout']    - comp_spec['Iout'])    <= tol * comp_spec['Iout'])
    )
 
    # 1.2-1 = 0.2 <= 0.5x1 = 0.5
 
    # -----------------------
    # 5) Frequency range overlap filter
    # -----------------------
   
    freq_mask = df.apply(
        lambda row: frequency_overlap_ratio(
            comp_spec['Freq_min'], comp_spec['Freq_max'],
            row['Freq_min'], row['Freq_max']
        ) <= min_freq_overlap_ratio,
        axis=1
    )
 
    # single_freq_mask = (
    #     (df['Freq'] <= comp_spec['Freq_max']) &
    #     (df['Freq'] >= comp_spec['Freq_min'])
    # )
 
    # print(single_freq_mask == True)
    # print(freq_mask == True)
 
    mask &= freq_mask 
   
    if boolean_package == 'yes':
        mask &= (df['Package']      == comp_spec['Package'])
        mask &= (abs(df['Width'] - comp_spec['Width']) == 0)
        mask &= (abs(df['Length'] - comp_spec['Length']) == 0)
    mask &= (df['Topology']     == comp_spec['Topology'])
 
    # print(mask)
    cand = df[mask].copy()
    print(cand)
   
    # 3) (You can skip pkg_size_sim/pkg_sim/topo_sim since you already filtered them)
    for field in ['Vin_min','Vin_max','Iout']:
        comp = comp_spec[field]
        cand[f'{field}_sim'] = (
            1 - (cand[field] - comp).abs() / comp
        ).clip(0,1)
 
    # Frequency similarity = actual overlap ratio
    cand['Freq_sim'] = cand.apply(
        lambda row: frequency_overlap_ratio(
            comp_spec['Freq_min'], comp_spec['Freq_max'],
            row['Freq_min'], row['Freq_max']
        ),
        axis=1
    )
 
    # 4) Weighted sum — now only numeric fields:
 
    weights = {
 
        'Vin_min_sim': 0.25,
 
        'Vin_max_sim': 0.25,
 
        'Iout_sim':    0.25,
 
        'Freq_sim':    0.25,
 
    }
 
    # normalize
 
    total_w = sum(weights.values())
 
    weights = {k: v/total_w for k,v in weights.items()}
 
    cand['Score'] = sum(cand[k]*w for k,w in weights.items())
 
 
    return (
 
        cand.sort_values('Score', ascending=False)
 
            [['PartNumber','Score']]
 
            .head(top_n)
 
    )
 
 
def main():
    # 1. Call the model
    partnumber = input("enter part number to cross and company:" )
    boolean_package = input("Do you want to check for same package (yes) or (no) : " )
 
    #scrap pdf first
    selenium_TI(partnumber)
    # 2. pdf to text
    pdf_to_text(partnumber)
    # 3. llm understand pdf and gives output features
 
            # Load your extracted datasheet text
    with open("output.txt", "r", encoding="utf-8") as f:
        datasheet_text = f.read()
 
    # Create a prompt for LLaMA
    prompt = f"""
    You are a strict extractor. From the following TI datasheet text,
    return **only** a JSON array of **exactly nine** values (no keys, no code fences, no preamble, no comments):
    Vin is usually found like input voltage range and it must be in the document , if there is no 'Vin_min'
    or 'Vin_max' specified and has "range up to" or single Vin , set it as Vin_max and Vin_min = 0
    Iout_max is the maximum current in peak usually in amperes(A)
    Frequency can either be a single number or a range like x KHz to y KHz and make sure
    its in MHz where KHz to MHz conversion is divide by 1000 and always have values in MHz
    which is usually < triple digits
    If frequency is a range, return both `Freq_min` and `Freq_max` values, otherwise if its a "fixed" frequency
    set the 'Freq_min' and 'Freq_max' value as the same "fixed" frequency . If theres only single value with
    "Range up to" , take that value as 'Freq_max' and set 'Freq_min' as 0 .
    'Package Size' should have no dimension like 'mm' with no space between dimension and has
    the format of WidthxLength where first number of dimension is always the width and
    second values is the length
    Package should be for example QFN , SOTxxx etc
    There should only be 9 output features that is very important :
 
    [Vin_min, Vin_max, Iout_max , Freq_min , Freq_max , "Package" , Width , Length, "Topology"]
 
    - Use `null` for missing numeric fields.
    - `Topology` must be "buck", "boost", or "buck-boost".
 
 
    make sure output format is just an array only , and look for the answer in the
    datasheet , all the answer to the array should be there
 
 
    Datasheet:
    {datasheet_text}
    """
    response = chat(prompt)
    print(response)
    # 4. filtering and reconmendation system
    result = algorithm(response , boolean_package)
    print(result)
if __name__ == "__main__":
   
    main()

