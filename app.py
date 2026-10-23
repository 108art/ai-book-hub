import html
import requests
import xml.etree.ElementTree as ET
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

AFFILIATE_TAG = "yourtrack-20"  # <- put your real Amazon tracking ID here
COPYRIGHTED_TERMS = ["harry potter", "percy jackson", "lord of the rings", "hobbit",
                     "stephen king", "twilight", "narnia"]
UA = {"User-Agent": "BookHubApp/1.0"}

st.set_page_config(page_title="The Book Hub", page_icon="📖", layout="centered")

CSS = """
<style>
.stApp{background:radial-gradient(circle at 50% 0%,#4a3321,#160e08 80%)}
#MainMenu,footer{visibility:hidden}
.block-container{max-width:780px;padding-top:2rem}
[data-testid="stForm"]{background:linear-gradient(145deg,#6b3a1f,#3e2012 60%,#2a150a);
 border:3px solid #d4a94a;border-radius:6px 18px 18px 6px;padding:3rem 2.2rem;
 box-shadow:inset 0 0 0 8px #3e2012,inset 0 0 0 10px #d4a94a,14px 16px 30px rgba(0,0,0,.6),-10px 0 0 #2a150a;
 animation:fade 1.2s ease-out}
.cover-title{font-family:Georgia,serif;color:#e8c872;text-align:center;font-size:2.3rem;
 letter-spacing:.2em;text-shadow:0 2px 4px #000;margin-bottom:.3rem}
.cover-sub{font-family:Georgia,serif;color:#d4a94a;text-align:center;font-style:italic;margin-bottom:1.5rem}
[data-testid="stForm"] label p,[data-testid="stForm"] div[role="radiogroup"] p{color:#e8c872!important}
[data-testid="stForm"] input{background:#f6ecd2;color:#2b1d12}
[data-testid="stForm"] button,.stButton button{background:#d4a94a;color:#2a150a;border:none;font-weight:700}
.book{perspective:1800px}
.page{background:linear-gradient(90deg,#e9dcb8,#f8efd6 6%,#f6ecd2);color:#2b1d12;
 font-family:Georgia,serif;padding:1.6rem 2rem;margin-bottom:1.2rem;border-radius:2px 10px 10px 2px;
 box-shadow:inset 8px 0 14px -8px rgba(0,0,0,.35),4px 6px 14px rgba(0,0,0,.5);
 transform-origin:left center;opacity:0;animation:flip .9s ease-out forwards}
.page h1{font-size:1.9rem;margin:.3rem 0}
.page h3{border-bottom:1px solid #b99a5a;padding-bottom:.4rem;color:#5a3418}
.page a{color:#8a4b12;font-weight:bold}
.page .bk{border-bottom:1px dotted #b99a5a;padding:.6rem 0}
.page .warn{background:#f1d9a8;border-left:4px solid #a4561b;padding:.7rem 1rem}
.page small{color:#6b5a44}
.loader{text-align:center;color:#e8c872;font-family:Georgia,serif;padding:2rem 0;perspective:900px}
.lbook{position:relative;width:114px;height:84px;margin:0 auto 1rem;background:#6b3a1f;border-radius:3px}
.lp{position:absolute;left:50%;top:2px;width:54px;height:80px;background:#f6ecd2;
 border:1px solid #b99a5a;transform-origin:left center;animation:lf 1.5s infinite ease-in-out}
.lp:nth-child(2){animation-delay:.25s}.lp:nth-child(3){animation-delay:.5s}
@keyframes lf{0%{transform:rotateY(0)}60%,100%{transform:rotateY(-170deg)}}
@keyframes flip{from{opacity:0;transform:rotateY(-100deg)}to{opacity:1;transform:rotateY(0)}}
@keyframes fade{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
</style>
"""
LOADER = ('<div class="loader"><div class="lbook"><div class="lp"></div><div class="lp"></div>'
          '<div class="lp"></div></div>Opening the book...</div>')
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def e(x):
    return html.escape(" ".join(str(x).split()))


def get_json(url, **params):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def text_of(v):
    if isinstance(v, dict):
        v = v.get("value", "")
    return (v or "").strip()


@lru_cache(maxsize=256)
def work_desc(key):
    d = text_of(get_json(f"https://openlibrary.org{key}.json").get("description"))
    return d.split("\n\n")[0][:600]


@lru_cache(maxsize=256)
def wiki(title):
    j = get_json("https://en.wikipedia.org/api/rest_v1/page/summary/"
                 + requests.utils.quote(title.replace(" ", "_")))
    return j.get("extract", "")


def amazon(q):
    return f"https://www.amazon.com/s?k={requests.utils.quote(q)}&tag={AFFILIATE_TAG}"


def free_link(d, title):
    ia = d.get("ia") or []
    if d.get("public_scan_b") and ia and not any(t in title.lower() for t in COPYRIGHTED_TERMS):
        return f"https://archive.org/details/{ia[0]}"
    return None


COPY_NOTE = ('<div class="warn">⚠️ <b>Copyright protected.</b> No free copy is offered here. '
             'Please buy an official copy.</div>')
DISCLOSE = "<small>As an Amazon Associate I earn from qualifying purchases.</small>"


def buy_page(query):
    return ("Where to buy", f'<p>🛒 <a href="{amazon(query)}" target="_blank">Buy on Amazon</a></p>{DISCLOSE}')


def not_found():
    return [("Not found", "<p>Nothing matched your search. Try different words.</p>")]


# ---------- searches ----------
def search_book(q):
    docs = get_json("https://openlibrary.org/search.json", q=q, limit=1,
                    fields="key,title,author_name,first_publish_year,ia,public_scan_b").get("docs", [])
    if not docs:
        return not_found()
    d = docs[0]
    title = d.get("title", q)
    author = ", ".join(d.get("author_name", ["Unknown author"]))
    desc = work_desc(d["key"]) or wiki(title) or "No description available."
    link = free_link(d, title)
    read = (f'<p>📄 <a href="{link}" target="_blank">Read / download the PDF (free)</a></p>'
            if link else COPY_NOTE)
    return [
        ("", f'<div style="text-align:center"><h1>{e(title)}</h1><p><i>by {e(author)}</i></p>'
             f'<p>First published {e(d.get("first_publish_year", "N/A"))}</p></div>'),
        ("Contents", "<ol><li>About this book</li><li>Read it / PDF link</li><li>Where to buy</li></ol>"),
        ("About this book", f"<p>{e(desc)}</p>"),
        ("Read it", read),
        buy_page(f"{title} {author}"),
    ]


def search_author(q):
    a = get_json("https://openlibrary.org/search/authors.json", q=q, limit=1).get("docs", [])
    if not a:
        return not_found()
    a = a[0]
    name = a.get("name", q)
    bio = text_of(get_json(f"https://openlibrary.org/authors/{a['key']}.json").get("bio")) or wiki(name)
    docs = get_json("https://openlibrary.org/search.json", author=name, limit=12, sort="editions",
                    fields="key,title,first_publish_year,ia,public_scan_b").get("docs", [])
    books, seen = [], set()
    for b in docs:
        t = b.get("title", "").lower()
        if t and t not in seen:
            seen.add(t)
            books.append(b)
    books = books[:10]
    with ThreadPoolExecutor(max_workers=5) as ex:
        descs = list(ex.map(lambda b: work_desc(b["key"]), books))
    cards = ""
    for i, (b, d) in enumerate(zip(books, descs), 1):
        link = free_link(b, b["title"])
        status = (f'<a href="{link}" target="_blank">📄 Free PDF / read online</a>' if link
                  else "<small>© Copyright protected</small>")
        cards += (f'<div class="bk"><b>{i}. {e(b["title"])}</b> <small>({e(b.get("first_publish_year", "n/a"))})</small>'
                  f'<br>{e(d) if d else "<small>No description available.</small>"}<br>{status}</div>')
    life = " - ".join(x for x in [a.get("birth_date", ""), a.get("death_date", "")] if x)
    toc = "".join(f"<li>{e(b['title'])}</li>" for b in books)
    return [
        ("", f'<div style="text-align:center"><h1>{e(name)}</h1><p><i>{e(life)}</i></p>'
             f'<p>{e(a.get("work_count", ""))} works listed</p></div>'),
        ("Index of books", f"<ol>{toc}</ol>"),
        ("About the author", f"<p>{e(bio[:900]) if bio else 'No biography available.'}</p>"),
        ("Their books", cards or "<p>No books found.</p>"),
        buy_page(f"{name} books"),
    ]


def search_paper(q):
    try:
        r = requests.get("https://export.arxiv.org/api/query",
                         params={"search_query": f'all:"{q}"', "max_results": 1}, timeout=15)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        en = ET.fromstring(r.content).find("a:entry", ns)
    except Exception:
        en = None
    if en is None:
        return not_found()
    title = en.find("a:title", ns).text
    summ = en.find("a:summary", ns).text
    auth = ", ".join(x.find("a:name", ns).text for x in en.findall("a:author", ns))
    pdf = next((l.get("href") for l in en.findall("a:link", ns) if l.get("title") == "pdf"), None)
    pdf = pdf.replace("http://", "https://") if pdf else None
    return [
        ("", f'<div style="text-align:center"><h1>{e(title)}</h1><p><i>{e(auth)}</i></p></div>'),
        ("Summary", f"<p>{e(summ)[:900]}</p>"),
        ("Read it", f'<p>📄 <a href="{pdf}" target="_blank">Open the free PDF</a></p>' if pdf
         else "<p>No PDF link found.</p>"),
    ]


def render(pages):
    out = '<div class="book">'
    for i, (head, body) in enumerate(pages):
        h = f"<h3>{head}</h3>" if head else ""
        out += f'<div class="page" style="animation-delay:{i * 0.5}s">{h}{body}</div>'
    return out + "</div>"


# ---------- app ----------
if "pages" in st.session_state:
    st.markdown(render(st.session_state["pages"]), unsafe_allow_html=True)
    if st.button("📕 Close book"):
        del st.session_state["pages"]
        st.rerun()
else:
    with st.form("cover"):
        st.markdown('<div class="cover-title">THE BOOK HUB</div>'
                    '<div class="cover-sub">✦ Find any book, author or paper ✦</div>',
                    unsafe_allow_html=True)
        mode = st.radio("Search for", ["Book", "Author", "Research paper"], horizontal=True)
        q = st.text_input("Type a title, name or topic")
        go = st.form_submit_button("Open the book 📖")
    if go and q.strip():
        ph = st.empty()
        ph.markdown(LOADER, unsafe_allow_html=True)
        fn = {"Book": search_book, "Author": search_author, "Research paper": search_paper}[mode]
        pages = fn(q.strip())
        ph.empty()
        st.session_state["pages"] = pages
        st.rerun()
