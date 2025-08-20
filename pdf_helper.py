# backend/pdf_helper.py
import fitz   # PyMuPDF
from pathlib import Path

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
