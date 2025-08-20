# app.py
# app.py
import platform
import asyncio
if platform.system() == "Windows":
    # Use the Windows loop that can spawn subprocesses
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import streamlit as st
from pathlib import Path
from backend import cross_algo
from backend.selenium_helper import selenium
from backend.pdf_helper import pdf_to_text
from backend.chat_with_ollama import chat  # your own wrapper
import json
import os
import pathlib
import streamlit as st
import fitz          # PyMuPDF

@st.cache_data(show_spinner=False)
def get_pdf_bytes(path: Path) -> bytes:
    """Return the raw PDF bytes – cached and pickle‑safe."""
    with open(path, "rb") as f:
        return f.read()

def show_pdf_first_two_pages(pdf_path: Path) -> None:
    """Open the PDF from bytes, display first 2 pages, and offer a download."""
    pdf_bytes = get_pdf_bytes(pdf_path)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for i in range(2):
        page = doc.load_page(i)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        st.image(
            img_bytes,
            caption=f"Datasheet – Page {i + 1}",
            use_container_width="auto"
        )
    st.download_button(
        label="📁 Download PDF again",
        data=pdf_path.read_bytes(),
        file_name=pdf_path.name,
        mime="application/pdf"
    )
# ------------------------------------------------------------------
# 1.  Helper – read the extracted text file
# ------------------------------------------------------------------
def read_output_txt() -> str:
    txt_path = Path.cwd() / "output.txt"
    if not txt_path.exists():
        st.warning("output.txt is missing – run the pipeline first.")
        return ""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()
# ------------------------------------------------------------------
# 2.  The main button‑callback that calls the whole pipeline
# ------------------------------------------------------------------
def run_pipeline(part_number: str, same_package: str):
    # ---- 2‑step cache ------------------------------------------------
    # Download & convert to text – both are cached so we don’t hit TI every time
    with st.spinner("Downloading PDF …"):
        pdf_path = selenium(part_number)  # returns Path to PDF
    with st.spinner("Extracting text …"):
        pdf_to_text(part_number)              # writes output.txt
    # ---- 3‑step LLM extraction ------------------------------------------------
    with open("output.txt", "r", encoding="utf-8") as f:
        datasheet_text = f.read()
       # Create a prompt for LLaMA
    prompt = f"""
    You are a strict extractor. From the following TI datasheet text,
    return **only** a JSON array of values (no keys, no code fences, no preamble, no comments):
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
    IQ is the quiescent current in the datasheet and it is in (uA)
    
    if the part is a "buck converter" or "step down" then there should only be 9 output features that is very important : 
    ["Topology", Vin_min, Vin_max, Iout_max , Freq_min , Freq_max , "Package" , Width , Length]
    else if its a "boost converter" or "step-up" then there should only be 12 output features that is very important : 
    ["Topology", Vin_min, Vin_max, Freq_min , Freq_max , "Package" , Width , Length, Vout_min , Vout_max , IQ ]
    - Use `null` for missing numeric fields.
    - `Topology` must be "buck", "boost", or "buck-boost".

    make sure output format is just an array only , and look for the answer in the 
    datasheet , all the answer to the array should be there 

    Datasheet:
    {datasheet_text}
    """
    with st.spinner("Querying the LLM …"):
        response = chat(prompt)
    st.info("LLM output (raw text):")
    st.text_area("LLM Response", value=response, height=200)
    # ---- 4‑step algorithm filtering ------------------------------------------------
    with st.spinner("Filtering & recommendation …"):
        result = cross_algo.algorithm_main(
            response=response,
            boolean_package=same_package,
            tol=0.8,
            top_n=10,
            min_freq_overlap_ratio=0.1
        )
    st.success("Result:")
    df = result
        # 3. Convert raw score → percentage string
    df["Percentage"] = (df["Score"] * 100).round(1).astype(str) + "%"

    # 4. Keep only the two columns you want to display
    display_df = df[["PartNumber", "Percentage","Topology","Vin_min","Vin_max","Iout", "Freq_min", "Freq_max","Package", "Width" , "Length"]]

    # 5. Show in Streamlit
    st.title("Part‑Number vs Similar Percentage %")

    #   * st.table → static table, nice for short lists
    st.table(display_df)

    #   * (optional) st.dataframe → interactive (sortable, scrollable)
    # st.dataframe(display_df)

    # 6. Optional: allow user to download the CSV
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="part_number_percentages.csv",
        mime="text/csv",
    )
    # st.json(result.to_dict(orient="records"))

        # *** NEW: display PDF only if it exists ***
    pdf_path = Path.cwd() / "downloads" / f"{part_number}.pdf"
    if pdf_path.exists():
        show_pdf_first_two_pages(pdf_path)
    else:
        st.warning("PDF not found – try re‑running the pipeline.")

#------------------------------------------------------------------
# 3.  Streamlit layout
# ------------------------------------------------------------------
st.set_page_config(page_title="TI Datasheet Cross‑Check", layout="wide")
st.title("TI DC-DC regulators Cross Reference Tool")
with st.sidebar:
    st.header("Input")
    part_number = st.text_input(
        "TI part number (e.g. `TPS628501`)",
        value="",
        placeholder="Enter part number here…"
    )
    same_package = st.radio(
        "Check same package?",
        options=["yes", "no"],
        index=0
    )
    if st.button("Search for Crosses"):
        if not part_number.strip():
            st.error("Please enter a part number.")
        else:
            run_pipeline(part_number.strip(), same_package)

# ------------------------------------------------------------------
# 4.  Optional: show the extracted text for debugging
# ------------------------------------------------------------------
if st.checkbox("Show extracted text", value=False):
    try:
        txt = read_output_txt()
        st.text_area("Extracted text (raw)", txt, height=300)
    except FileNotFoundError:
        st.warning("output.txt has not been created yet.")
