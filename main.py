import streamlit as st
from openai import OpenAI
from streamlit import secrets
import tempfile
import time
import os

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

def process_uploaded_file(uploaded_file):
    """Process the uploaded file and create an OpenAI file."""
    if not uploaded_file:
        return None
    
    temp_file = None
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1])

        temp_file.write(uploaded_file.getvalue())
        temp_file.seek(0)
        
        message_file = client.files.create(
            file=open(temp_file.name, "rb"),
            purpose="assistants"
        )
        
        return message_file
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None
    
    finally:
        # Clean up resources
        if temp_file:
            temp_file.close()
            try:
                os.unlink(temp_file.name)  # Delete the temporary file
            except Exception as e:
                st.warning(f"Could not delete temporary file: {str(e)}")

def main():
    st.title("Document Explainer")
    
    # Create assistant if not already created
    if 'assistant' not in st.session_state:
        with st.spinner('Initializing assistant...'):
            st.session_state.assistant = create_assistant()
    
    uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt", "doc", "docx"])
    
    if uploaded_file is not None:
        if st.button("Analyze Document"):
            with st.spinner('Processing document...'):
                # Process the uploaded file
                message_file = process_uploaded_file(uploaded_file)
                
                if message_file:
                # Create a thread with the file attachment
                    thread = client.beta.threads.create(
                        messages=[{
                            "role": "user",
                            "content": "Please analyze this document and provide a clear explanation for the general public.",
                            "file_ids": [message_file.id]
                        }]
                    )
                
                   
                else:
                    st.error("Failed to process the uploaded file.")
                


if __name__ == "__main__":
    main()