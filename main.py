import requests
import streamlit as st
from openai import OpenAI
from streamlit import secrets
from dotenv import load_dotenv

load_dotenv()

# OpenAI API
# get the API key from the environment variables
client = OpenAI(
    # This is the default and can be omitted
    api_key=secrets["OPENAI_KEY"],
)

# set OpenAI's API URL
OPENAI_API_URL = "https://api.openai.com/v1/engines/davinci/completions"


def create_main_layout():
    st.title("Document Explainer")
    
     # Dropdown for input selection
    input_type = st.selectbox(
        "Select Input Type",
        ["Document Upload", "Text Input", "URL Input"],
        placeholder="Select..."
    )
    
    # Show different input methods based on selection
    if input_type == "Document Upload":
        uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            st.success("File uploaded successfully!")
            
    elif input_type == "Text Input":
        text_input = st.text_area("Enter your text here...")
        if text_input:
            st.info(f"Text received: {len(text_input)} characters")
            
    else:  # URL Input
        url_input = st.text_input("Enter URL", placeholder="https://example.com")
        if url_input:
            st.info("URL received")


create_main_layout();