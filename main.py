import streamlit as st
from openai import OpenAI
from streamlit import secrets
import tempfile
import os
import json
import re

# Initialize OpenAI client
client = OpenAI(api_key=secrets["OPENAI_KEY"])

def create_assistant():
    """Create an OpenAI assistant for document analysis."""
    try:
        assistant = client.beta.assistants.create(
            name="Document Explainer",
            instructions="""Transform complex and jargon-heavy sources into a straightforward journalistic explainer that is accessible to the general public.

Clearly organize the explainer with journalistic language, comprehensive subsections, concrete takeaways, and explanations of relevance. Assume readers are not experts and may require additional context for complex topics.

When referring to specific information or quotes from the source document, add citation markers like [citation] which will later be converted to interactive citations.

# Steps

1. **Understand the Source Material**: Thoroughly review the original sources to comprehend the main ideas and jargon used.

2. **Identify Key Points**: Extract the most important information and concepts that need to be conveyed to the reader.

3. **Provide Context**: For complex topics, break down the jargon and provide contextual background for better understanding.

4. **Organize the Content**: Structure the explainer into clear subsections that guide the reader through the information logically.

5. **Use Clear Language**: Aim for clarity and simplicity in language to ensure the content is accessible to all readers.

6. **Highlight Relevance**: Explain why the information is important and how it affects the everyday life of the reader.

7. **Conclude with Takeaways**: Summarize the main points and provide concrete takeaways that reinforce the reader's understanding.

# Output Format

- Structured into clearly defined sections with subsections as needed.
- Use headings to organize the content.
- Paragraphs should be concise with simple language.
- Include relevant background information where necessary.
- End with a summary and concise takeaways.
- Add file citations with the file_citation tool for direct quotes or specific information from the source document.

# Examples

**Example 1 (Input):** 

Source text uses terms like "quantitative easing," "monetary policy," and "fiscal stimulus" without explanation.

**Example 1 (Output):**

- **Introduction**: Briefly introduce the economic measures being discussed.
- **Understanding Quantitative Easing**: Explain in simple terms, mentioning it as a tool used by central banks to stimulate the economy by increasing money supply.
- **Monetary vs. Fiscal Policy**: Differentiate between the two, providing examples of each.
- **Relevance to You**: Discuss how these policies might affect interest rates and consumer prices, which could impact loans and savings.
- **Conclusion**: Recap the key points and why staying informed on these topics is beneficial.

# Notes

- Use analogies and real-world examples where possible to make complex ideas relatable.
- Keep sentences short and focus on one idea at a time to avoid overwhelming the reader.
- Always circle back to the relevance to the reader's everyday life to maintain engagement.
- When using direct quotes or specific information, use the file_citation tool to reference the source document.
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
        temp_file.close()  # CLOSE the file before reopening it

        # Upload the file to OpenAI
        with open(temp_file.name, "rb") as f:
            message_file = client.files.create(file=f, purpose="assistants")

        return message_file

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

    finally:
        # Clean up the temporary file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

def extract_citations(message):
    """Extract citations from the assistant's message."""
    citations = []
    
    # Get the text content
    if not message.content or not message.content[0].text:
        return [], ""
    
    text_object = message.content[0].text
    content = text_object.value
    
    # Extract annotations (citations)
    annotations = text_object.annotations
    
    # Process each annotation
    for i, annotation in enumerate(annotations):
        if annotation.type == "file_citation":
            # Get the text being cited
            cited_text = content[annotation.start_index:annotation.end_index]
            
            # Get the file citation information
            file_citation = annotation.file_citation
            
            # Retrieve the cited content using the file search API
            try:
                # We'll use the file_id to identify the citation, but we won't actually 
                # fetch the content here as it requires additional API calls
                citations.append({
                    "index": i,
                    "text": cited_text,
                    "quote": cited_text,  # Use the cited text as the quote for now
                    "file_id": file_citation.file_id
                })
            except Exception as e:
                st.warning(f"Could not retrieve citation {i}: {str(e)}")
                citations.append({
                    "index": i,
                    "text": cited_text,
                    "quote": "Citation content unavailable",
                    "file_id": file_citation.file_id
                })
            
            # Replace the citation in the content with a marker
            citation_marker = f"[{i}]"
            content = content[:annotation.start_index] + citation_marker + content[annotation.end_index:]
            
            # Adjust the indices of subsequent annotations
            offset = len(citation_marker) - (annotation.end_index - annotation.start_index)
            for j in range(i + 1, len(annotations)):
                annotations[j].start_index += offset
                annotations[j].end_index += offset
    
    return citations, content

def get_file_content(file_id):
    """Get file content from OpenAI."""
    try:
        response = client.files.content(file_id)
        content = response.read().decode("utf-8")
        return content
    except Exception as e:
        st.warning(f"Could not retrieve file content: {str(e)}")
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
        messages = list(client.beta.threads.messages.list(thread_id=thread_id))

        if not messages:
            return "No response received from the assistant.", []

        # Get the latest message from the assistant
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if not assistant_messages:
            return "No response received from the assistant.", []
        
        latest_message = assistant_messages[0]
        
        # Extract citations and processed content
        citations, processed_content = extract_citations(latest_message)
        
        # Try to retrieve the actual quoted content for each citation
        for citation in citations:
            if citation["file_id"]:
                # We'll use the file search API in a real application
                # For now, we'll use the text we have
                pass
                
        # Check if there's a JSON block in the response
        json_match = re.search(r"```json\n(.*?)\n```", processed_content, re.DOTALL)
        if json_match:
            # Extract the JSON and remove it from the displayed content
            json_str = json_match.group(1)
            try:
                citations_json = json.loads(json_str)
                # Convert JSON citations to our format if needed
                for key, quote in citations_json.items():
                    # Try to match with existing citations by index
                    index = int(key)
                    
                    # Update existing citation or add new one
                    existing = next((c for c in citations if c["index"] == index), None)
                    if existing:
                        existing["quote"] = quote
                    else:
                        citations.append({
                            "index": index,
                            "text": f"[{index}]",
                            "quote": quote,
                            "file_id": None
                        })
                
                # Remove the JSON block from the content
                processed_content = processed_content.replace(json_match.group(0), "")
            except json.JSONDecodeError:
                st.warning("Failed to parse citations JSON. Displaying content as is.")
        
        return processed_content, citations
    
    except Exception as e:
        st.error(f"Error running analysis: {str(e)}")
        return None, []

def generate_css():
    """Generate CSS for the tooltip functionality."""
    return """
    <style>
    .citation {
        color: #0066cc;
        cursor: pointer;
        position: relative;
        text-decoration: underline;
        font-weight: bold;
    }
    
    .tooltip {
        visibility: hidden;
        width: 300px;
        background-color: #f8f9fa;
        color: #212529;
        text-align: left;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -150px;
        opacity: 0;
        transition: opacity 0.3s;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        border: 1px solid #e9ecef;
        font-weight: normal;
    }
    
    .citation:hover .tooltip {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """

def format_content_with_citations(content, citations):
    """Format content with interactive citations."""
    formatted_content = content
    
    # Replace citation markers with interactive spans
    for citation in sorted(citations, key=lambda x: x["index"], reverse=True):
        index = citation["index"]
        marker = f"[{index}]"
        quote = citation["quote"]
        
        html_citation = f'<span class="citation">{marker}<span class="tooltip">{quote}</span></span>'
        formatted_content = formatted_content.replace(marker, html_citation)
    
    return formatted_content

def main():
    st.title("Document Explainer")
    
    # Inject CSS for tooltips
    st.markdown(generate_css(), unsafe_allow_html=True)
    
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
                            "content": """Please analyze this document and provide a clear explanation for the general public. 
                            Use file citations when referencing specific information or direct quotes from the document.
                            Make the explanation engaging and accessible, breaking down complex concepts and jargon.
                            Organize the content with clear sections and highlight the relevance to everyday readers.
                            
                            For each citation reference you make, also include the actual quoted text from the document in a JSON
                            object at the end of your response, with the citation index as the key and the quoted text as the value.
                            
                            For example:
                            ```json
                            {
                                "0": "The actual text from the document that citation 0 refers to",
                                "1": "The actual text from the document that citation 1 refers to"
                                "2": "The actual text from the document that citation 2 refers to",
                                "3": "The actual text from the document that citation 3 refers to"
                                "4": "The actual text from the document that citation 4 refers to",
                                "5": "The actual text from the document that citation 5 refers to"
                            }
                            ```
                            
                            This will allow me to display the quoted text when users hover over the citations.""",
                            "attachments": [{"file_id": message_file.id, "tools": [{"type": "file_search"}] }]
                        }]
                    )
                    
                    # Run the analysis
                    content, citations = run_assistant_analysis(st.session_state.assistant.id, thread.id)
                    
                    if content:
                        # Format content with interactive citations
                        formatted_content = format_content_with_citations(content, citations)
                        
                        # Display the formatted content
                        st.markdown(formatted_content, unsafe_allow_html=True)
                        
                        # Display citations separately for reference
                        if citations:
                            with st.expander("View all citations"):
                                for citation in citations:
                                    st.markdown(f"**[{citation['index']}]** {citation['quote']}")
                    else:
                        st.error("Failed to get analysis from the assistant.")
                else:
                    st.error("Failed to process the uploaded file.")

if __name__ == "__main__":
    main()