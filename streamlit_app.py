# Importing required packages
import streamlit as st
import openai
import uuid
import time
import pandas as pd
import io
from openai import OpenAI

openai_api_key = st.secrets["OPENAI_API_KEY"]
openai_assistant = st.secrets["OPENAI_ASSISTANT"]

print(f"OpenAI API Key: {openai_api_key}")
print(f"OpenAI Assistant ID: {openai_assistant}")
# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

initial_message = """Good day to you! Welcome to Lux Retreats! Thank you for your interest in our villas 🤩

We have two villas available, The Black Box Villa and The White Box Villa 🏘️ Both villas are conveniently located next to each other. Our clients have the option to rent them individually for small gatherings or book both villas for larger events. Please find the pricing details below:"""

# Your chosen model
MODEL = "gpt-3.5-turbo-1106"

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "run" not in st.session_state:
    st.session_state.run = {"status": None}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "retry_error" not in st.session_state:
    st.session_state.retry_error = 0

def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

# Set up the page
st.set_page_config(page_title="Lux Retreats Demo")
st.sidebar.title("Lux Retreats Demo")

# # File uploader for CSV, XLS, XLSX
# uploaded_file = st.file_uploader("Upload your file", type=["csv", "xls", "xlsx"])

# if uploaded_file is not None:
#     # Determine the file type
#     file_type = uploaded_file.type

#     try:
#         # Read the file into a Pandas DataFrame
#         if file_type == "text/csv":
#             df = pd.read_csv(uploaded_file)
#         elif file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
#             df = pd.read_excel(uploaded_file)

#         # Convert DataFrame to JSON
#         json_str = df.to_json(orient='records', indent=4)
#         file_stream = io.BytesIO(json_str.encode())

#         # Upload JSON data to OpenAI and store the file ID
#         file_response = client.files.create(file=file_stream, purpose='answers')
#         st.session_state.file_id = file_response.id
#         st.success("File uploaded successfully to OpenAI!")

#         # Optional: Display and Download JSON
#         st.text_area("JSON Output", json_str, height=300)
#         st.download_button(label="Download JSON", data=json_str, file_name="converted.json", mime="application/json")
    
#     except Exception as e:
#         st.error(f"An error occurred: {e}")

st.caption("""Welcome to Lux Retreats! Thank you for your interest in our villas 🤩! I'm happy to assist you on your holiday planning! Feel free to ask me anything!""")


# Initialize OpenAI assistant
if "assistant" not in st.session_state:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.assistant = openai.beta.assistants.retrieve(st.secrets["OPENAI_ASSISTANT"])
    st.session_state.thread = client.beta.threads.create(
        metadata={'session_id': st.session_state.session_id}
    )

# Display chat messages
elif hasattr(st.session_state.run, 'status') and st.session_state.run.status == "completed":
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread.id
    )
    for message in reversed(st.session_state.messages.data):
        if message.role in ["user", "assistant"]:
            with st.chat_message(message.role):
                for content_part in message.content:
                    message_text = content_part.text.value
                    st.markdown(message_text)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
else:
    st.session_state["messages"] = [{"role": "assistant", "content" : initial_message}]

# Chat input and message creation with file ID
if prompt := st.chat_input(""):
    with st.chat_message('user'):
        st.write(prompt)

    message_data = {
        "thread_id": st.session_state.thread.id,
        "role": "user",
        "content": prompt
    }

    # Include file ID in the request if available
    if "file_id" in st.session_state:
        message_data["file_ids"] = [st.session_state.file_id]

    st.session_state.messages = client.beta.threads.messages.create(**message_data)

    st.session_state.run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
    )

    run = wait_on_run(st.session_state.run, st.session_state.thread)

    if st.session_state.retry_error < 3:
        time.sleep(1)
        st.rerun()

# Handle run status
if hasattr(st.session_state.run, 'status'):
    if st.session_state.run.status == "running":
        with st.chat_message('assistant'):
            st.write("Thinking ......")
        if st.session_state.retry_error < 3:
            time.sleep(1)
            st.rerun()

    elif st.session_state.run.status == "failed":
        st.session_state.retry_error += 1
        with st.chat_message('assistant'):
            if st.session_state.retry_error < 3:
                st.write("Run failed, retrying ......")
                time.sleep(3)
                st.rerun()
            else:
                st.error("FAILED: The OpenAI API is currently processing too many requests. Please try again later ......")

    elif st.session_state.run.status != "completed":
        st.session_state.run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread.id,
            run_id=st.session_state.run.id,
        )
        if st.session_state.retry_error < 3:
            time.sleep(3)
            st.rerun()