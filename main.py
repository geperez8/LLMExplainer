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

def process_uploaded_file(vector_store_id, uploaded_file):
    """Process uploaded file and add it to the vector store."""
    if not uploaded_file:
        return None

    temp_file = None
    file_stream = None
    
    try:
        # Create a temporary file to store the document
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1])
        
        # Write the uploaded content to the temporary file
        temp_file.write(uploaded_file.getvalue())
        temp_file.seek(0)

        file_stream = open(temp_file.name, "rb")
        
        # Upload file to vector store
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store_id,
            files=[file_stream]
        )


        
        return file_batch
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

    finally:
        if file_stream:
            file_stream.close()
        if temp_file:
            temp_file.close()
            os.unlink(temp_file.name)
        

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
                # Create a vector store for this file
                vector_store = create_vector_store(f"store_{uploaded_file.name}")
                
                if vector_store:
                    # Process the uploaded file
                    file_batch = process_uploaded_file(vector_store.id, uploaded_file)

if __name__ == "__main__":
    main()