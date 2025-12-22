import streamlit as st
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="SEO Master: Clean & Translate", page_icon="🌍", layout="wide")

# --- CHARACTER CLEANING (MOJIBAKE FIX) ---
def clean_text(text):
    """Fixes common character encoding glitches (Mojibake)."""
    if not text: return ""
    replacements = {
        "â€™": "'", "â€˜": "'", "â€œ": '"', "â€": '"',
        "â€”": "-", "â€“": "-", "â€•": "-", "â€¢": "•",
        "ðŸ™‚": "🙂", "ðŸ˜Š": "😊", "Â": ""
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    # Remove hidden null bytes and excessive whitespace
    text = text.replace('\x00', '').strip()
    return text

# --- SIDEBAR: API KEYS ---
with st.sidebar:
    st.header("🔑 API Setup")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    aff_id = st.text_input("Amazon Associate ID", value="mytag-20")
    st.divider()
    model_choice = "gemini-2.0-flash-lite" # Best free-tier balance
    st.info(f"Using Model: {model_choice}")

st.title("🚀 SEO Content Master")
st.caption("Cleans encoding errors & translates foreign URLs to English automatically.")

# --- CORE FUNCTIONS ---
def get_amazon_link(product_name, s_key, s_id, a_id):
    if not s_key or not s_id: return None
    url = f"https://www.googleapis.com/customsearch/v1?q=site:amazon.com {product_name}&key={s_key}&cx={s_id}"
    try:
        data = requests.get(url).json()
        link = data['items'][0]['link']
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', link)
        return f"https://www.amazon.com/dp/{asin.group(1)}/?tag={a_id}" if asin else None
    except: return None

def generate_with_retry(client, prompt, model_name, max_retries=3):
    for i in range(max_retries):
        try:
            return client.models.generate_content(model=model_name, contents=prompt)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = (2 ** i) + random.random()
                st.warning(f"Quota busy. Waiting {wait:.1f}s... (Attempt {i+1})")
                time.sleep(wait)
            else: raise e
    return None

# --- UI SECTIONS ---
col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Input Source:", ["URL Scraper", "Manual Text Input", "Idea/Topic Only"])
    user_input = st.text_area("Paste Content or URL here:", height=200)

with col2:
    main_topic = st.text_input("Main Topic / Keyword")
    extra_instructions = st.text_input("Special Instructions (e.g. Tone, Audience)")

# --- EXECUTION ---
if st.button("🔥 Generate English SEO Package"):
    if not gemini_key:
        st.error("Please provide an API Key.")
    else:
        with st.spinner("Processing... (Cleaning & Translating if needed)"):
            try:
                client = genai.Client(api_key=gemini_key)
                
                # Scraper logic with encoding fix
                source_content = user_input
                if mode == "URL Scraper" and user_input.startswith("http"):
                    resp = requests.get(user_input, headers={'User-Agent': 'Mozilla/5.0'})
                    # Force UTF-8 decoding to prevent mojibake at the source
                    resp.encoding = resp.apparent_encoding
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    source_content = soup.get_text()[:6000]

                # --- AI PROMPT (ENFORCED TRANSLATION) ---
                prompt = f"""
                CONTEXT: You are a professional SEO Content Writer.
                SOURCE CONTENT (Might be in a foreign language): {source_content if source_content else main_topic}
                
                TASK:
                1. If the source content is NOT in English, TRANSLATE it to English first.
                2. Use the (translated) ideas to write a high-quality blog post.
                3. Ensure the output is clean English with NO encoding errors (like â€™).
                
                OUTPUT REQUIREMENTS:
                [TITLES] - 3 SEO Friendly Titles.
                [TAGS] - 15 comma-separated tags.
                [PROMPTS] - 3 detailed Text-to-Image prompts.
                [HTML] - The full blog in HTML (H1, H2, H3, bolding, 3x [[PRODUCT: Name]] placeholders).
                
                Special Focus: {main_topic}
                Extra Instructions: {extra_instructions}
                """

                response = generate_with_retry(client, prompt, model_choice)
                
                if response:
                    raw_text = clean_text(response.text) # CLEAN MOJIBAKE HERE
                    
                    # Parsing
                    titles = re.search(r"\[TITLES\](.*?)\[TAGS\]", raw_text, re.S).group(1).strip()
                    tags = re.search(r"\[TAGS\](.*?)\[PROMPTS\]", raw_text, re.S).group(1).strip()
                    img_prompts = re.search(r"\[PROMPTS\](.*?)\[HTML\]", raw_text, re.S).group(1).strip()
                    blog_html = re.search(r"\[HTML\](.*)", raw_text, re.S).group(1).strip()

                    # Link Injection
                    found_products = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                    for p in found_products:
                        link = get_amazon_link(p, search_key, search_id, aff_id)
                        if link:
                            blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}" target="_blank" style="color:#FF9900; font-weight:bold;">{p} (Amazon)</a>')

                    # Final Result Display
                    tab1, tab2, tab3 = st.tabs(["📄 Preview", "📈 SEO Data", "🎨 Image Prompts"])
                    with tab1:
                        st.markdown(blog_html, unsafe_allow_html=True)
                    with tab2:
                        st.write("**Titles:**", titles)
                        st.write("**Tags:**", tags)
                    with tab3:
                        st.info("Paste these into an AI Image Generator:")
                        st.code(img_prompts)

                    st.download_button("💾 Download .html", blog_html, "seo_post.html", "text/html")
            
            except Exception as e:
                st.error(f"Error: {e}")
