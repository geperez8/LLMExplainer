import streamlit as st
from openai import OpenAI
from streamlit import secrets
import tempfile
import time

# Initialize OpenAI client
client = OpenAI(api_key=secrets["OPENAI_KEY"])

def create_assistant():
    """Create an OpenAI assistant for document analysis."""
    try:
        assistant = client.beta.assistants.create(
            name="Document Explainer",
            instructions="""You are a journalist who is trying to write an explainer for the general public. 
            You are tasked with taking sources that use a lot of jargon and can be confusing for general readers. 
            You have to make your explainer straightforward, with journalistic language, clear subsections, 
            concrete takeaways, and reasons for why this information is relevant to the everyday reader.""",
            model="gpt-4o",
            tools=[{"type": "file_search"}]
        )
        return assistant
    except Exception as e:
        st.error(f"Error creating assistant: {str(e)}")
        return None


def create_vector_store(store_name):
    """Create a new vector store with the given name."""
    try:
        return client.beta.vector_stores.create(name=store_name)
    except Exception as e:
        st.error(f"Error creating vector store: {str(e)}")
        return None

