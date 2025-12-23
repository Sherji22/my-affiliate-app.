import streamlit as st
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="SEO Content Bypass", page_icon="🔓", layout="wide")

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

# --- REPAIRED AMAZON SEARCH FUNCTION ---
def get_amazon_link(product_name, s_key, s_id, a_id):
    """Stronger search logic to ensure affiliate link generation."""
    if not s_key or not s_id or not product_name: 
        return None
    
    # We clean the product name and force the search to look at Amazon
    search_query = f"site:amazon.com {product_name}"
    url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={s_key}&cx={s_id}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        # DEBUG: Let the user know if items are found
        if "items" in data:
            for item in data["items"]:
                link = item["link"]
                # Try to extract the ASIN (The 10-character Amazon ID)
                asin_match = re.search(r'/(?:dp|gp/product|product-reviews)/([A-Z0-9]{10})', link)
                if asin_match:
                    asin = asin_match.group(1)
                    return f"https://www.amazon.com/dp/{asin}/?tag={a_id}"
        else:
            # If no items, the search engine might be restricted
            st.sidebar.warning(f"No Amazon results for '{product_name}'. check CSE settings.")
    except Exception as e:
        st.sidebar.error(f"Search API Error: {e}")
    return None

# --- SIDEBAR: API KEYS ---
with st.sidebar:
    st.header("🔑 API Setup")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    aff_id = st.text_input("Amazon Associate ID", value="mytag-20")
    st.divider()
    model_choice = st.selectbox("Model Strategy", 
                            ["gemini-2.0-flash", "gemini-2.0-flash-lite"], 
                            help="Flash-Lite is usually best for free-tier quotas.")

st.title("🚀 SEO Content Master (Clean & Link)")

# --- CORE FUNCTIONS ---
def generate_with_retry(client, prompt, model_name, max_retries=3):
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
    return None

# --- UI SECTIONS ---
col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Input Source:", ["URL Scraper", "Manual Text", "Idea/Topic Only"])
    user_content = st.text_area("Details/URL", height=150)
with col2:
    main_topic = st.text_input("Focus Keyword (e.g., 'Camping Gear')")
    extra_instructions = st.text_input("Target Audience (e.g., 'Beginners')")

# --- EXECUTION ---
if st.button("🔥 Generate SEO Package"):
    if not all([gemini_key, search_key, search_id]):
        st.error("Please fill in ALL API keys in the sidebar!")
    else:
        with st.spinner("Processing..."):
            try:
                client = genai.Client(api_key=gemini_key)
                
                # Scraper Logic with Encoding Fix for Russian/Foreign text
                if mode == "URL Scraper" and user_content.startswith("http"):
                    resp = requests.get(user_content, headers={'User-Agent': 'Mozilla/5.0'})
                    resp.encoding = resp.apparent_encoding 
                    user_content = BeautifulSoup(resp.text, 'html.parser').get_text()[:5000]

                # TRANSLATION + SEO PROMPT
                prompt = f"""
                Act as an SEO Specialist and Translator. 
                If the following content is not in English, translate it to English first.
                CONTENT: {user_content if user_content else main_topic}
                TARGET: {extra_instructions}
                
                REQUIREMENTS:
                1. Write 3 Titles and 15 Tags.
                2. Write a Full Blog in HTML.
                3. Place 3 product placeholders EXACTLY like this: [[PRODUCT: Specific Item Name]]
                
                Format the response with these headers: [TITLES], [TAGS], [HTML], [PROMPTS].
                """

                response = generate_with_retry(client, prompt, model_choice)
                
                if response:
                    # Clean Mojibake characters (Itâ€™s -> It's)
                    full_text = clean_text(response.text)
                    
                    # Split result
                    blog_html = full_text.split("[HTML]")[-1].strip()
                    
                    # Amazon Link Replacement
                    found = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                    for p in found:
                        st.info(f"🔎 Searching for {p}...")
                        link = get_amazon_link(p, search_key, search_id, aff_id)
                        if link:
                            blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}" target="_blank" style="color:#FF9900; font-weight:bold;">{p} (Buy on Amazon)</a>')
                        else:
                            blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f"<strong>{p}</strong>")

                    st.tabs(["📄 Preview", "📈 Meta Data"])[0].markdown(blog_html, unsafe_allow_html=True)
                    st.download_button("💾 Save HTML", blog_html, "article.html", "text/html")
            except Exception as e:
                st.error(f"Critical System Error: {e}")
