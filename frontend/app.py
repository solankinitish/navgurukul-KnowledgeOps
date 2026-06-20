import streamlit as st
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def create_session():
    response = requests.post(f"{BASE_URL}/session/create")
    return response.json()["session_id"]

def get_loaded_pdfs():
    response = requests.get(f"{BASE_URL}/pdfs")
    return response.json().get("pdfs", [])

def stream_query(session_id, query):
    chunks_data = []
    latency = None
    response_text = ""

    with requests.post(
        f"{BASE_URL}/session/{session_id}/query",
        json={"query": query},
        stream=True,
        timeout=60
    ) as response:
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    token = decoded[6:]
                    if token == "[DONE]":
                        break
                    elif token.startswith("CHUNKS:"):
                        chunks_data = json.loads(token[7:])
                    elif token.startswith("LATENCY:"):
                        latency = float(token[8:])
                    else:
                        response_text += token
                        yield "token", token, chunks_data, latency

    yield "done", response_text, chunks_data, latency

# --- Init ---
if "session_id" not in st.session_state:
    st.session_state.session_id = create_session()
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Page ---
st.set_page_config(page_title="navgurukul-KnowledgeOps", layout="wide")
st.title("NavGurukul-KnowledgeOps")
st.caption("RAG Chatbot over PDFs with hybrid retrieval and source citations")

# --- Sidebar ---
with st.sidebar:
    st.header("📚 Loaded Documents")
    pdfs = get_loaded_pdfs()
    if pdfs:
        for pdf in pdfs:
            st.markdown(f"📄 {pdf}")
    else:
        st.info("No documents loaded yet. Run the ingestion script.")
    
    st.divider()
    st.header("⬆️ Upload PDF")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded_file:
        if st.button("Ingest", use_container_width=True):
            with st.spinner(f"Ingesting {uploaded_file.name}..."):
                response = requests.post(
                    f"{BASE_URL}/ingest",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                )
            if response.status_code == 200:
                st.success(response.json()["message"])
                st.rerun()
            else:
                st.error(response.json().get("detail", "Ingestion failed"))

# --- Chat history ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "chunks" in message:
            with st.expander(f"📎 Retrieved chunks - {message.get('latency', '?')}s"):
                for i, chunk in enumerate(message["chunks"]):
                    st.markdown(f"""**Chunk {i+1}** | 📄 `{chunk['pdf_filename']}` |
                                Page `{chunk['page_number']}` |
                                Score `{chunk['score']}` |
                                `{chunk['extraction_method']}`
                                """)
                    st.caption(chunk["text"])
                    st.divider()

# --- Chat input ---
if prompt := st.chat_input("Ask a question about your documents..."):
    if not pdfs and not get_loaded_pdfs():
        st.warning("No documents loaded. Please ingest PDFs first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            answer_placeholder = st.empty()
            full_response = ""
            final_chunks = []
            final_latency = None

            for event, data, chunks, latency in stream_query(st.session_state.session_id, prompt):
                if event == "token":
                    full_response += data
                    answer_placeholder.markdown(full_response)
                    final_chunks = chunks
                    final_latency = latency
                elif event == "done":
                    final_chunks = chunks
                    final_latency = latency
            
            if final_chunks:
                with st.expander(f"📎 Retrieved chunks — {final_latency}s"):
                    for i, chunk in enumerate(final_chunks):
                        st.markdown(f"""**Chunk {i+1}** | 📄 `{chunk['pdf_filename']}` |
                                    Page `{chunk['page_number']}` |
                                    Score `{chunk['score']}` |
                                    `{chunk['extraction_method']}`""")
                        st.caption(chunk["text"])
                        st.divider()
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "chunks": final_chunks,
            "latency": final_latency
        })
