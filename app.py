import streamlit as st
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="SEO Content Bypass", page_icon="🔓", layout="wide")

# --- SIDEBAR: API KEYS ---
with st.sidebar:
    st.header("🔑 API Setup")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    aff_id = st.text_input("Amazon Associate ID", value="mytag-20")
    st.divider()
    # Allowing model selection in case 1.5 also fails
    model_choice = st.selectbox("Model Strategy", 
                                ["gemini-1.5-flash", "gemini-2.0-flash-lite"], 
                                help="1.5 Flash is most likely to work without a credit card.")

st.title("🚀 SEO Content Master (No-Card Bypass Mode)")

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
    """Robust retry logic for free tier stability."""
    for i in range(max_retries):
        try:
            return client.models.generate_content(model=model_name, contents=prompt)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                wait = (2 ** i) + random.random()
                st.warning(f"Quota issue. Waiting {wait:.1f}s... (Attempt {i+1})")
                time.sleep(wait)
            else:
                st.error(f"API Error: {err_msg}")
                return None
    st.error("❌ Still blocked. Google may require credit card verification for this model.")
    return None

# --- UI SECTIONS ---
col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Input Source:", ["Idea/Topic Only", "URL Scraper", "Manual Text"])
    user_content = st.text_area("Details/URL", height=150)
with col2:
    main_topic = st.text_input("Focus Keyword (e.g., 'Camping Gear')")
    extra_instructions = st.text_input("Target Audience (e.g., 'Beginners')")

# --- EXECUTION ---
if st.button("🔥 Generate SEO Package"):
    if not gemini_key:
        st.error("Please enter your API Key!")
    else:
        with st.spinner(f"Using {model_choice} to generate..."):
            try:
                client = genai.Client(api_key=gemini_key)
                
                # Scraper Logic
                if mode == "URL Scraper" and user_content.startswith("http"):
                    resp = requests.get(user_content, headers={'User-Agent': 'Mozilla/5.0'})
                    user_content = BeautifulSoup(resp.text, 'html.parser').get_text()[:5000]

                prompt = f"""
                Act as an SEO Specialist. Create a high-quality blog for: {user_content if user_content else main_topic}.
                Targeting: {extra_instructions}.
                Include: 3 titles, 15 tags, and the blog in HTML with 3x [[PRODUCT: Name]] placeholders.
                Format clearly with labels: [TITLES], [TAGS], [HTML], [PROMPTS].
                """

                response = generate_with_retry(client, prompt, model_choice)
                
                if response:
                    full_text = response.text
                    
                    # Split result (using simpler logic to avoid regex errors)
                    blog_html = full_text.split("[HTML]")[-1].strip()
                    metadata = full_text.split("[HTML]")[0]

                    # Amazon Link Replacement
                    found = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                    for p in found:
                        link = get_amazon_link(p, search_key, search_id, aff_id)
                        if link:
                            blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}" target="_blank" style="color:#FF9900; font-weight:bold;">{p}</a>')

                    st.tabs(["📄 Preview", "📈 Meta Data"])[0].markdown(blog_html, unsafe_allow_html=True)
                    st.download_button("💾 Save HTML", blog_html, "article.html", "text/html")
            except Exception as e:
                st.error(f"Critical System Error: {e}")
