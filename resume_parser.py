import fitz


def extract_text_from_pdf(uploaded_file):
    pdf_bytes = uploaded_file.read()

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text.strip()