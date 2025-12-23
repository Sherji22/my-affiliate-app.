import streamlit as st
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="SEO Master Pro", page_icon="🚀", layout="wide")

# --- CHARACTER CLEANING (MOJIBAKE FIX) ---
def clean_text(text):
    if not text: return ""
    replacements = {
        "â€™": "'", "â€˜": "'", "â€œ": '"', "â€": '"',
        "â€”": "-", "â€“": "-", "Â": "", "Ã©": "e", "Ã": "a"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.strip()

# --- AMAZON SEARCH LOGIC ---
def get_amazon_link(product_name, s_key, s_id, a_id):
    """Searches Google for the Amazon product and builds a clean affiliate link."""
    if not s_key or not s_id or not product_name:
        return None
    
    # Clean the product name for searching
    search_query = f"site:amazon.com {product_name}"
    url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={s_key}&cx={s_id}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if "items" in data:
            for item in data["items"]:
                link = item["link"]
                # Extract ASIN (The 10-digit Amazon product ID)
                asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', link)
                if asin_match:
                    asin = asin_match.group(1)
                    # Construct a CLEAN affiliate link
                    return f"https://www.amazon.com/dp/{asin}/?tag={a_id}"
    except Exception as e:
        print(f"Search Error: {e}")
    return None

# --- SIDEBAR: CONFIG ---
with st.sidebar:
    st.header("🔑 Setup")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    aff_id = st.text_input("Amazon Associate ID", value="mytag-20")
    st.divider()
    st.info("Ensuring Russian/Foreign -> English translation + Amazon Linking.")

st.title("🚀 SEO Content & Affiliate Master")

# --- UI INPUTS ---
col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Input Source:", ["URL Scraper", "Manual Text Input", "Idea Only"])
    user_input = st.text_area("Input (URL or Text):", height=200)
with col2:
    main_topic = st.text_input("Main Topic / Keyword")
    extra_instructions = st.text_input("Special Focus (Audience, Tone, etc.)")

# --- MAIN ENGINE ---
if st.button("🔥 Generate English SEO Package"):
    if not all([gemini_key, search_key, search_id]):
        st.error("Please fill in ALL API keys in the sidebar.")
    else:
        with st.spinner("Analyzing, Translating, and Finding Products..."):
            try:
                client = genai.Client(api_key=gemini_key)
                source_content = user_input

                # Handle URL Scraping & Translation
                if mode == "URL Scraper" and user_input.startswith("http"):
                    resp = requests.get(user_input, headers={'User-Agent': 'Mozilla/5.0'})
                    resp.encoding = resp.apparent_encoding # Fix Russian/Foreign encoding
                    source_content = BeautifulSoup(resp.text, 'html.parser').get_text()[:6000]

                # AI PROMPT (Strict English + Linking Instructions)
                prompt = f"""
                Act as a professional SEO Content Writer and Translator.
                SOURCE: {source_content if source_content else main_topic}
                
                TASK:
                1. TRANSLATE the content to natural, high-converting English.
                2. WRITE a full blog post optimized for SEO.
                3. IDENTIFY 3 specific products mentioned and wrap them exactly like this: [[PRODUCT: Item Name]]
                
                FORMAT:
                [TITLES] (3 Titles)
                [TAGS] (15 comma-separated)
                [PROMPTS] (3 Image Prompts)
                [HTML] (Full HTML Article)
                """

                response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
                raw_text = clean_text(response.text)

                # Parse and Search
                blog_html = raw_text.split("[HTML]")[-1].strip()
                
                # Locate and replace product placeholders with REAL Amazon Links
                placeholders = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                for item_name in placeholders:
                    real_link = get_amazon_link(item_name, search_key, search_id, aff_id)
                    if real_link:
                        link_html = f'<a href="{real_link}" target="_blank" style="color:#FF9900; font-weight:bold;">{item_name} (View on Amazon)</a>'
                        blog_html = blog_html.replace(f"[[PRODUCT: {item_name}]]", link_html)
                    else:
                        blog_html = blog_html.replace(f"[[PRODUCT: {item_name}]]", f"<strong>{item_name}</strong>")

                st.tabs(["📄 Final Blog", "🎨 Image Prompts"])[0].markdown(blog_html, unsafe_allow_allow_html=True)
                st.download_button("💾 Download .html File", blog_html, "seo_post.html", "text/html")

            except Exception as e:
                st.error(f"Critical Error: {e}")
