import streamlit as st
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro SEO Content Creator", page_icon="📝", layout="wide")

# --- SIDEBAR: API KEYS ---
with st.sidebar:
    st.header("🔑 API Setup (Free)")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    aff_id = st.text_input("Amazon Associate ID", value="mytag-20")
    st.divider()
    st.info("Using Gemini 2.0 Flash-Lite + Auto-Retry Logic.")

st.title("🚀 One-Click SEO & Affiliate Content Master")

# --- CORE FUNCTIONS ---

def get_amazon_link(product_name, s_key, s_id, a_id):
    """Google Search for Amazon products (100 free/day)."""
    if not s_key or not s_id: return None
    url = f"https://www.googleapis.com/customsearch/v1?q=site:amazon.com {product_name}&key={s_key}&cx={s_id}"
    try:
        data = requests.get(url).json()
        link = data['items'][0]['link']
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', link)
        return f"https://www.amazon.com/dp/{asin.group(1)}/?tag={a_id}" if asin else None
    except: return None

def generate_with_retry(client, prompt, model_name="gemini-2.0-flash-lite", max_retries=5):
    """Generates content with Exponential Backoff retry logic."""
    for i in range(max_retries):
        try:
            return client.models.generate_content(model=model_name, contents=prompt)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                # Wait: (2^retry * 2 seconds) + some random jitter
                wait_time = (2 ** i) + (random.randint(1, 1000) / 1000)
                st.warning(f"Rate limit hit. Retrying in {wait_time:.2f} seconds... (Attempt {i+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise e # If it's a different error, stop immediately
    raise Exception("Max retries exceeded. Please wait a minute and try again.")

# --- UI SECTIONS ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input Method")
    mode = st.radio("Choose source:", ["URL Scraper", "Manual Text Input", "Idea/Topic Only"])
    user_content = ""
    if mode == "URL Scraper":
        source_url = st.text_input("Paste Source URL")
    elif mode == "Manual Text Input":
        user_content = st.text_area("Paste your own draft here", height=250)
    else:
        user_content = st.text_area("Enter ideas (e.g., '6 best Christmas gifts for techies')", height=150)

with col2:
    st.subheader("2. Target Settings")
    main_topic = st.text_input("Main Topic / Keyword")
    extra_instructions = st.text_input("Special Instructions (Optional)")

# --- PROCESSING ---
if st.button("🔥 Generate Full SEO Package"):
    if not gemini_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
    else:
        with st.spinner("Analyzing and writing... (This may include auto-retries)"):
            try:
                client = genai.Client(api_key=gemini_key)
                
                if mode == "URL Scraper" and source_url:
                    resp = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    user_content = soup.get_text()[:6000]

                # --- AI PROMPT ---
                prompt = f"""
                Act as an Expert SEO Content Strategist.
                TOPIC: {user_content if user_content else main_topic}
                INSTRUCTIONS: {extra_instructions}

                TASK: Generate an SEO package with:
                1. THREE SEO TITLES
                2. 15 SEO TAGS (comma separated)
                3. BLOG POST in HTML (H1, H2, H3, bolding, 3x [[PRODUCT: Name]] placeholders)
                4. THREE IMAGE PROMPTS

                OUTPUT FORMAT:
                [TITLES]
                (Titles here)
                [TAGS]
                (Tags here)
                [PROMPTS]
                (Prompts here)
                [HTML]
                (HTML here)
                """

                # Using the retry function
                response = generate_with_retry(client, prompt)
                full_text = response.text

                # --- PARSING ---
                titles = re.search(r"\[TITLES\](.*?)\[TAGS\]", full_text, re.S).group(1).strip()
                tags = re.search(r"\[TAGS\](.*?)\[PROMPTS\]", full_text, re.S).group(1).strip()
                img_prompts = re.search(r"\[PROMPTS\](.*?)\[HTML\]", full_text, re.S).group(1).strip()
                blog_html = re.search(r"\[HTML\](.*)", full_text, re.S).group(1).strip()

                # --- LINK INJECTION ---
                found_products = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                for p in found_products:
                    link = get_amazon_link(p, search_key, search_id, aff_id)
                    if link:
                        blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}" target="_blank" style="color:#FF9900; font-weight:bold;">{p}</a>')

                # --- DISPLAY ---
                tabs = st.tabs(["📄 Blog Preview", "📈 SEO & Metadata", "🎨 Image Prompts"])
                with tabs[0]: st.markdown(blog_html, unsafe_allow_html=True)
                with tabs[1]:
                    st.write("**Titles:**", titles)
                    st.write("**Tags:**", tags)
                with tabs[2]: st.write(img_prompts)

                st.download_button("💾 Download .html", blog_html, "post.html", "text/html")

            except Exception as e:
                st.error(f"Final Error: {e}")
