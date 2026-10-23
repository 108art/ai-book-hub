import os
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from pypdf import PdfReader  
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import TokenTextSplitter

# 1. Secure Credential Configurations
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY", "YOUR_FALLBACK_KEY_HERE")

AFFILIATE_TAG = "yourtrack-20"

# 2. Initialize global AI components
Settings.llm = Groq(model="llama3-8b-8192") 
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = TokenTextSplitter(chunk_size=512, chunk_overlap=32)

DATA_DIR = "./data"
IMAGE_DIR = "./extracted_images"
for folder in [DATA_DIR, IMAGE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

COPYRIGHTED_TERMS = ["harry potter", "percy jackson", "lord of the rings", "hobbit", "stephen king", "twilight", "narnia"]

def clear_old_assets():
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            try: os.remove(os.path.join(DATA_DIR, f))
            except: pass
    if os.path.exists(IMAGE_DIR):
        for f in os.listdir(IMAGE_DIR):
            try: os.remove(os.path.join(IMAGE_DIR, f))
            except: pass

# --- Streamlit Web Interface Setup ---
st.set_page_config(page_title="AI Commercial Book Engine", layout="wide")
st.title("📚 AI Multi-Source Book Hub & Monetized Finder")
st.subheader("Search libraries, download papers, extract graphics, and generate legal summaries.")

with st.sidebar:
    st.header("⚡ Commercial Dashboard")
    st.success("Cloud Brain Active")
    st.write("🔥 Monetization Layer Active via Amazon Associates System")

# --- Step 1: Broad Search Module ---
st.markdown("### 🔍 Search & Gather Portal")
search_input = st.text_input("Enter a Book Title, Author Name, or Research Topic:")
search_btn = st.button("Execute Search Engine")

if search_btn and search_input:
    clear_old_assets()
    query_lower = search_input.lower()
    
    # CHECK 1: Trademark/Copyright Safety Shield Protection
    if any(term in query_lower for term in COPYRIGHTED_TERMS):
        st.warning("⚠️ **Copyright Protection Triggered:** Direct downloading restricted. Re-routing to Open Summary Catalog data...")
        
        encoded_query = requests.utils.quote(search_input)
        ol_url = f"https://openlibrary.org{encoded_query}"
        
        display_title = search_input.title()
        display_author = ""
        summary_found = False
        
        try:
            ol_res = requests.get(ol_url, timeout=10)
            if ol_res.status_code == 200:
                json_data = ol_res.json()
                if json_data.get("docs") and len(json_data["docs"]) > 0:
                    book_data = json_data["docs"][0]
                    display_title = book_data.get("title", display_title)
                    display_author = ", ".join(book_data.get("author_name", ["Unknown Author"]))
                    first_publish = book_data.get("first_publish_year", "N/A")
                    
                    st.markdown(f"#### 📖 **Book Profile: {display_title}**")
                    st.markdown(f"* **Author:** {display_author}")
                    st.markdown(f"* **First Published:** {first_publish}")
                    summary_found = True
        except Exception as e:
            pass
            
        # FIXED WIKIPEDIA API ENGINE
        wiki_api_url = f"https://wikipedia.org{requests.utils.quote(display_title.replace(' ', '_'))}"
        try:
            wiki_res = requests.get(wiki_api_url, timeout=10)
            if wiki_res.status_code == 200:
                wiki_json = wiki_res.json()
                extract = wiki_json.get('extract', 'No explicit summary found.')
                if not summary_found:
                    st.markdown(f"#### 📖 **Book Profile: {display_title}**")
                st.info(f"**Brief Encyclopedic Summary:** {extract}")
            else:
                st.error("Could not locate metadata details for this title in the catalog registries.")
        except Exception as e:
            st.error(f"Error reading library databases: {e}")
            
        amazon_search_url = f"https://amazon.com{requests.utils.quote(display_title + ' ' + display_author)}&tag={AFFILIATE_TAG}"
        st.markdown(f"🛒 **[Buy Official Copy on Amazon]({amazon_search_url})** *(Affiliate Link - Earn Commissions)*")
            
    # CHECK 2: Open Source / Free Academic Document Downloader
    else:
        st.info("Target matches open license directories. Commencing automated web gathering...")
        payload = {'search_query': f'all:"{search_input}"', 'max_results': 1}
        api_url = "http://arxiv.org"
        
        with st.spinner("Hunting open repositories and downloading file streams..."):
            try:
                response = requests.get(api_url, params=payload, timeout=15)
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://w3.org'}
                
                pdf_link = None
                for entry in root.findall('atom:entry', ns):
                    for link in entry.findall('atom:link', ns):
                        if link.get('title') == 'pdf':
                            pdf_link = link.get('href')
                            break
                
                if pdf_link:
                    target_path = os.path.join(DATA_DIR, "active_document.pdf")
                    download_res = requests.get(pdf_link, timeout=15)
                    with open(target_path, "wb") as f:
                        f.write(download_res.content)
                    st.success("🎉 Success: Free Document downloaded into workspace storage!")
                    
                    reader_pdf = PdfReader(target_path)
                    img_count = 0
                    for page_num, page in enumerate(reader_pdf.pages):
                        if page.images:
                            for image_file_object in page.images:
                                img_path = os.path.join(IMAGE_DIR, f"extracted_p{page_num+1}_{img_count}_{image_file_object.name}")
                                with open(img_path, "wb") as fp:
                                    fp.write(image_file_object.data)
                                img_count += 1
                    if img_count > 0:
                        st.write(f"✨ Found and extracted **{img_count} internal images** from layout layers!")
                else:
                    st.warning("Could not find matching academic distributions on arXiv.")
            except Exception as e:
                st.error(f"Data stream retrieval error: {e}")

# --- Step 2: Display & Conversational Dashboard Layers ---
st.markdown("---")
tab1, tab2 = st.tabs(["💬 Document Chatbot Interface", "🖼️ Extracted Photo Gallery Index"])

with tab1:
    st.markdown("### Interactive Workspace Portal")
    if os.path.exists(DATA_DIR) and len(os.listdir(DATA_DIR)) > 0:
        reader = SimpleDirectoryReader(DATA_DIR)
        documents = reader.load_data()
        
        index = VectorStoreIndex.from_documents(documents, embed_model=Settings.embed_model)
        query_engine = index.as_query_engine(llm=Settings.llm)
        
        user_question = st.text_input("Type a message to discuss your active file:")
        if user_question:
            with st.spinner("AI Processing..."):
                res = query_engine.query(user_question)
                st.markdown(f"**Bot Answer:** {res}")
    else:
        st.info("The local work directory is empty. Execute a search query above to load files.")

with tab2:
    st.markdown("### Document Graphics Indexing Gallery")
    image_files = os.listdir(IMAGE_DIR) if os.path.exists(IMAGE_DIR) else []
    
    if image_files:
        st.write("Showing all image assets extracted from the active book layers:")
        cols = st.columns(3)
        for idx, img_file in enumerate(image_files):
            col_target = cols[idx % 3]
            img_path = os.path.join(IMAGE_DIR, img_file)
            col_target.image(img_path, caption=f"Asset: {img_file}", use_container_width=True)
    else:
        st.info("No graphics extracted yet. Load a valid PDF file layout to populate this page.")
