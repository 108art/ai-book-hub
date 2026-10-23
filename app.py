import os
import requests
import xml.etree.ElementTree as ET
import streamlit as st
from pypdf import PdfReader
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import TokenTextSplitter

# ---------------------------------------------------------------
# 1. Credentials (set GROQ_API_KEY in Streamlit Cloud > Secrets)
# ---------------------------------------------------------------
if "GROQ_API_KEY" not in os.environ:
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except Exception:
        st.error("Missing GROQ_API_KEY. Add it in App settings > Secrets.")
        st.stop()

AFFILIATE_TAG = "yourtrack-20"

# ---------------------------------------------------------------
# 2. AI components (cached so they load only once)
# ---------------------------------------------------------------
@st.cache_resource
def init_ai():
    Settings.llm = Groq(model="llama-3.1-8b-instant")
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.node_parser = TokenTextSplitter(chunk_size=512, chunk_overlap=32)
    return True

init_ai()

DATA_DIR = "./data"
IMAGE_DIR = "./extracted_images"
for folder in [DATA_DIR, IMAGE_DIR]:
    os.makedirs(folder, exist_ok=True)

COPYRIGHTED_TERMS = [
    "harry potter", "percy jackson", "lord of the rings",
    "hobbit", "stephen king", "twilight", "narnia",
]


def clear_old_assets():
    for folder in [DATA_DIR, IMAGE_DIR]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                try:
                    os.remove(os.path.join(folder, f))
                except Exception:
                    pass


@st.cache_resource(show_spinner="Reading and indexing document...")
def build_query_engine(file_stamp):
    """Builds the index once per file. file_stamp changes when the file changes."""
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    index = VectorStoreIndex.from_documents(documents)
    return index.as_query_engine()


# ---------------------------------------------------------------
# 3. Page setup
# ---------------------------------------------------------------
st.set_page_config(page_title="AI Commercial Book Engine", layout="wide")
st.title("📚 AI Multi-Source Book Hub & Monetized Finder")
st.subheader("Search libraries, download papers, extract graphics, and generate legal summaries.")

with st.sidebar:
    st.header("⚡ Commercial Dashboard")
    st.success("Cloud Brain Active")
    st.write("🔥 Monetization Layer Active via Amazon Associates")

# ---------------------------------------------------------------
# 4. Search module
# ---------------------------------------------------------------
st.markdown("### 🔍 Search & Gather Portal")
search_input = st.text_input("Enter a Book Title, Author Name, or Research Topic:")
search_btn = st.button("Execute Search Engine")

if search_btn and search_input:
    clear_old_assets()
    build_query_engine.clear()
    query_lower = search_input.lower()

    # CHECK 1: copyright protection
    if any(term in query_lower for term in COPYRIGHTED_TERMS):
        st.warning(
            "⚠️ **Copyright Protection Triggered:** Direct downloading restricted. "
            "Showing catalog info instead..."
        )

        encoded_query = requests.utils.quote(search_input)
        ol_url = f"https://openlibrary.org/search.json?q={encoded_query}&limit=1"

        display_title = search_input.title()
        display_author = ""
        summary_found = False

        try:
            ol_res = requests.get(ol_url, timeout=10)
            if ol_res.status_code == 200:
                json_data = ol_res.json()
                if json_data.get("docs"):
                    book_data = json_data["docs"][0]
                    display_title = book_data.get("title", display_title)
                    display_author = ", ".join(book_data.get("author_name", ["Unknown Author"]))
                    first_publish = book_data.get("first_publish_year", "N/A")

                    st.markdown(f"#### 📖 **Book Profile: {display_title}**")
                    st.markdown(f"* **Author:** {display_author}")
                    st.markdown(f"* **First Published:** {first_publish}")
                    summary_found = True
        except Exception:
            pass

        # Wikipedia summary
        wiki_title = requests.utils.quote(display_title.replace(" ", "_"))
        wiki_api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}"
        try:
            wiki_res = requests.get(
                wiki_api_url, timeout=10, headers={"User-Agent": "BookHubApp/1.0"}
            )
            if wiki_res.status_code == 200:
                extract = wiki_res.json().get("extract", "No explicit summary found.")
                if not summary_found:
                    st.markdown(f"#### 📖 **Book Profile: {display_title}**")
                st.info(f"**Brief Encyclopedic Summary:** {extract}")
            else:
                st.error("Could not find details for this title in the catalogs.")
        except Exception as e:
            st.error(f"Error reading library databases: {e}")

        amazon_query = requests.utils.quote(f"{display_title} {display_author}".strip())
        amazon_search_url = f"https://www.amazon.com/s?k={amazon_query}&tag={AFFILIATE_TAG}"
        st.markdown(
            f"🛒 **[Buy Official Copy on Amazon]({amazon_search_url})** "
            "*(Affiliate Link - Earn Commissions)*"
        )

    # CHECK 2: open academic papers from arXiv
    else:
        st.info("Searching open-access repositories...")
        payload = {"search_query": f'all:"{search_input}"', "max_results": 1}
        api_url = "http://export.arxiv.org/api/query"

        with st.spinner("Searching and downloading..."):
            try:
                response = requests.get(api_url, params=payload, timeout=15)
                root = ET.fromstring(response.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}

                pdf_link = None
                for entry in root.findall("atom:entry", ns):
                    for link in entry.findall("atom:link", ns):
                        if link.get("title") == "pdf":
                            pdf_link = link.get("href")
                            break

                if pdf_link:
                    if pdf_link.startswith("http://"):
                        pdf_link = pdf_link.replace("http://", "https://", 1)
                    target_path = os.path.join(DATA_DIR, "active_document.pdf")
                    download_res = requests.get(pdf_link, timeout=30)
                    with open(target_path, "wb") as f:
                        f.write(download_res.content)
                    st.success("🎉 Free document downloaded!")

                    reader_pdf = PdfReader(target_path)
                    img_count = 0
                    for page_num, page in enumerate(reader_pdf.pages):
                        try:
                            for image_file_object in page.images:
                                img_path = os.path.join(
                                    IMAGE_DIR,
                                    f"extracted_p{page_num + 1}_{img_count}_{image_file_object.name}",
                                )
                                with open(img_path, "wb") as fp:
                                    fp.write(image_file_object.data)
                                img_count += 1
                        except Exception:
                            continue
                    if img_count > 0:
                        st.write(f"✨ Extracted **{img_count} images** from the document!")
                else:
                    st.warning("Could not find a matching paper on arXiv.")
            except Exception as e:
                st.error(f"Data retrieval error: {e}")

# ---------------------------------------------------------------
# 5. Chat + gallery tabs
# ---------------------------------------------------------------
st.markdown("---")
tab1, tab2 = st.tabs(["💬 Document Chatbot", "🖼️ Extracted Photo Gallery"])

with tab1:
    st.markdown("### Interactive Workspace")
    files = os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else []

    if files:
        pdf_path = os.path.join(DATA_DIR, files[0])
        file_stamp = f"{files[0]}-{os.path.getmtime(pdf_path)}"
        query_engine = build_query_engine(file_stamp)

        user_question = st.text_input("Ask a question about your document:")
        if user_question:
            with st.spinner("AI is thinking..."):
                try:
                    res = query_engine.query(user_question)
                    st.markdown(f"**Bot Answer:** {res}")
                except Exception as e:
                    st.error(f"AI error: {e}")
    else:
        st.info("No document loaded yet. Run a search above.")

with tab2:
    st.markdown("### Document Graphics Gallery")
    image_files = os.listdir(IMAGE_DIR) if os.path.exists(IMAGE_DIR) else []

    if image_files:
        cols = st.columns(3)
        for idx, img_file in enumerate(image_files):
            img_path = os.path.join(IMAGE_DIR, img_file)
            try:
                cols[idx % 3].image(img_path, caption=img_file, use_container_width=True)
            except Exception:
                pass
    else:
        st.info("No images extracted yet.")
