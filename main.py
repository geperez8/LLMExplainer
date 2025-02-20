import streamlit as st
from openai import OpenAI
from streamlit import secrets
import tempfile
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

def process_uploaded_file(uploaded_file):
    """Process the uploaded file and create an OpenAI file."""
    if not uploaded_file:
        return None
    
    temp_file = None
    
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1])
        # Write the uploaded content to the temporary file
        temp_file.write(uploaded_file.getvalue())
        temp_file.seek(0)
        
        # Upload the file to OpenAI
        message_file = client.files.create(
            file=open(temp_file.name, "rb"),
            purpose="assistants"
        )
        
        return message_file
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def run_assistant_analysis(assistant_id, thread_id):
    """Run the assistant analysis and return the response."""
    try:
        # Create and poll the run
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Get the messages from the thread
        messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))
        
        

        message_content = messages[0].content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))

        for message in messages:
            if message.role == "assistant":
                return message.content[0].text.value
        
        return "No response received from the assistant."
    
    except Exception as e:
        st.error(f"Error running analysis: {str(e)}")
        return None

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
                # Upload file to OpenAI
                message_file = process_uploaded_file(uploaded_file)
                
                if message_file:
                    # Create a thread with the file attachment
                    thread = client.beta.threads.create(
                        messages=[{
                            "role": "user",
                            "content": "Please analyze this document and provide a clear explanation for the general public.",
                            "attachments": [{"file_id": message_file.id, "tools": [{"type": "file_search"}] }]
                        }]
                    )
                    
                    # Run the analysis
                    response = run_assistant_analysis(st.session_state.assistant.id, thread.id)
                    
                    if response:
                        st.markdown("## Analysis")
                        st.markdown(response)
                    else:
                        st.error("Failed to get analysis from the assistant.")
                else:
                    st.error("Failed to process the uploaded file.")

if __name__ == "__main__":
    main()