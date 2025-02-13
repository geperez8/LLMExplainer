import requests
import streamlit as st
from openai import OpenAI
from streamlit import secrets
from dotenv import load_dotenv
import fitz  # PyMuPDF
import numpy as np
from paddleocr import PaddleOCR
import pandas as pd

load_dotenv()

# OpenAI API
# get the API key from the environment variables
client = OpenAI(
    # This is the default and can be omitted
    api_key=secrets["OPENAI_KEY"],
)

# set OpenAI's API URL
OPENAI_API_URL = "https://api.openai.com/v1/engines/davinci/completions"

prompt = """You are a journalist who is trying to write an explainer for the general public. You are
tasked with taking sources that use a lot of jargon and can be confusing for general 
readers. You have to make your explainer straightforward, with journalistic language, 
clear subsections, concrete takeaways, and reasons for why this information is relevant 
to the everyday reader. Just give me the summarization and nothing else.
"""

def load_ocr_model(language='en', use_angle=True):
    try:
        return PaddleOCR(
            use_angle_cls=use_angle,
            lang=language,
            show_log=False
        )
    except Exception as e:
        st.error(f"Error loading OCR model: {str(e)}")
        return None

def perform_ocr(pdf_bytes, ocr_model):
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_results = []
        confidence_results = []
        total_pages = len(pdf_document)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page_num in range(total_pages):
            status_text.text(f"Processing page {page_num + 1} of {total_pages}")
            
            page = pdf_document[page_num]
            pix = page.get_pixmap()
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            
            result = ocr_model.ocr(img_array)
            
            page_text = []
            page_confidence = []
            
            if result[0]:
                for line in result[0]:
                    text = line[1][0]  # Text content
                    confidence = line[1][1]  # Confidence score
                    page_text.append(text)
                    page_confidence.append(confidence)
            
            text_results.append(f"Page {page_num + 1}:\n" + "\n".join(page_text) + "\n")
            confidence_results.append(page_confidence)
            
            progress_bar.progress((page_num + 1) / total_pages)
        
        pdf_document.close()
        status_text.empty()
        progress_bar.empty()

        text_results = '\n'.join(text_results)

        return text_results, confidence_results
        
    except Exception as e:
        return f"Error processing PDF: {str(e)}", None


def run_gpt(prompt, src_text):
    chat_completion = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\nAnalyze this text:\n{src_text}",
            }
        ],
        model="gpt-4o",
    )

    content = chat_completion.choices[0].message.content
    
    return content

def main():
    st.title("Document Explainer")
    
     # Dropdown for input selection
    input_type = st.selectbox(
        "Select Input Type",
        ["Document Upload", "Text Input"],
        placeholder="Select..."
    )
    
    # Show different input methods based on selection
    if input_type == "Document Upload":
        with st.spinner('Loading OCR model...'):
            ocr = load_ocr_model(language='en')
        
        if ocr:
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
            if uploaded_file is not None:
                if st.button("Run Model"):
                    with st.spinner('Processing PDF...'):
                        pdf_bytes = uploaded_file.read()
                        text_results, confidence_results = perform_ocr(pdf_bytes, ocr)
                    
                    with st.spinner('Running model...'):
                        llm_response = run_gpt(prompt, text_results)
                    
                    st.markdown(llm_response)
            
    elif input_type == "Text Input":
        text_input = st.text_area("Enter your text here...", height=400)
        if st.button("Run Model") and text_input:
            llm_response = run_gpt(prompt, text_input)
            st.markdown(llm_response)

if __name__ == "__main__":
    main()