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
            You are tasked with taking sources that use a lot of jargon and can be confusing for general readers
            and making them more digestable. You have to make your explainer straightforward, with journalistic 
            language, clear subsections, concrete takeaways, and reasons for why this information is relevant 
            to the everyday reader. Assume the reader has a is not an expert in the field and would need additional
            context when it comes to very complex topics.
            """,
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
    """Run the assistant analysis and extract citation-related text."""
    try:
        # Run the assistant on the given thread
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Retrieve messages from the thread
        messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))

        if not messages:
            return "No response received from the assistant."

        message_content = messages[0].content[0].text  # Main assistant response
        print(message_content)
        annotations = getattr(message_content, "annotations", [])

        extracted_citations = []

        print(annotations)

        # Extract text associated with each citation
        for annotation in annotations:
            if annotation.type == "file_citation":  # Check for citation type
                cited_text = message_content.value[annotation.start_index:annotation.end_index]
                extracted_citations.append({
                    "citation_marker": annotation.text,
                    "extracted_text": cited_text
                })

        # Replace citation markers in the response with indexed references
        response_text = message_content.value

        # extract json
        # json_extract_pattern = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
        # json_extract = json_extract_pattern.search(txt).group(1)
        for index, annotation in enumerate(annotations):
            response_text = response_text.replace(annotation.text, f"[{index}]")

        # Display extracted citations
        citation_display = "\n".join([f"[{i}] {c['citation_marker']}: {c['extracted_text']}" for i, c in enumerate(extracted_citations)])

        # Print output for debugging
        # print(response_text)
        print(citation_display)

        return response_text
    
    except Exception as e:
        st.error(f"Error running analysis: {str(e)}")
        return None


thread_instructions = """
    Please analyze this document and provide a clear explanation for the general public. 
    Adiitionally, return a json object with every single citation being referenced in the 
    text. In the json object, the key should be the citation marker within the explainer response 
    and the value should be the reference text from the original document. Every single reference
    in the explainer response should have an attributed text in the json of citations. There 
    should be a one-to-one correspondence between the citation markers in the explainer response
    and the references in the json object.

    # Output format

    The output should contain the main explanation for the general public, which may include context, 
    key findings, why it matters to ther everyday reader, and a conclusion. Include whatever additional 
    information you deem important. There should also be a json object containing the citations. Here is 
    an example response for the json of quotes from the source document and how you should format it:

    ```json
    {
        "0": "In the present paper, we provide extensive new experimental evidence to inform the claim that LLMs are equally capable of learning possible and impossible languages in the human sense.",
        "1": "Chomsky and others have very directly claimed that LLMs are equally capable of learning languages that are possible and impossible for humans to learn.",
        "2": "Our core finding is that GPT-2 struggles to learn impossible languages when compared to English as a control, challenging the core claim.",
        "3": "Our experiments can inform the core hypotheses as follows: if LLMs learn these languages as well as they learn natural languages, then the claims of Chomsky and others are supported.",
        "4": "These authors state this claim in absolute terms. For example, Chomsky et al. (2023) flatly assert that LLMs 'are incapable of distinguishing the possible from the impossible'.",
        "5": "Our paper complements this line of work, providing evidence for the utility of LLMs as models of language learning.",
        "6": "At the same time, conclusions about LLMs’ linguistic competence and preferences for natural languages should be informed by an understanding of the ways that models fundamentally differ from humans.",
        "7": "The current paper raises further questions along similar lines. Since we do find that real languages are more learnable by GPT-2, this leads us to wonder what inductive bias the GPTs have which matches natural language.",
        "8": "We believe that this inductive bias is related to information locality, the tendency for statistical correlations in text to be relatively short-range.",
        "9": "Contra claims by Chomsky and others that LLMs cannot possibly inform our understanding of human language, we argue there is great value in treating LLMs as a comparative system for human language and in understanding what systems like LLMs can and cannot learn."
    }
    ```

    """


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
                            "content": thread_instructions,
                            "attachments": [{"file_id": message_file.id, "tools": [{"type": "file_search"}] }]
                        }]
                    )
                    
                    # Run the analysis
                    response = run_assistant_analysis(st.session_state.assistant.id, thread.id)
                    
                    if response:
                        st.markdown(response)
                    else:
                        st.error("Failed to get analysis from the assistant.")
                else:
                    st.error("Failed to process the uploaded file.")

if __name__ == "__main__":
    main()