import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
from google import genai
from io import BytesIO

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
    st.info("No Imagen 3 needed. This app uses Gemini 2.0 Flash (Free Tier).")

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

# --- UI SECTIONS ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input Method")
    mode = st.radio("Choose source:", ["URL Scraper", "Manual Text Input", "Idea/Topic Only"])
    
    source_url = ""
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
        with st.spinner("Analyzing trends and writing content..."):
            try:
                client = genai.Client(api_key=gemini_key)
                
                # Fetch content if URL mode
                if mode == "URL Scraper" and source_url:
                    resp = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    user_content = soup.get_text()[:6000]

                # --- AI PROMPT ---
                prompt = f"""
                Act as an Expert SEO Content Strategist.
                TOPIC/CONTENT: {user_content if user_content else main_topic}
                INSTRUCTIONS: {extra_instructions}

                TASK: Generate a complete SEO-optimized blog package.
                
                1. THREE SEO TITLES: Creative, high-CTR, and AI-Search friendly.
                2. SEO TAGS: Comma-separated list of 15 keywords.
                3. BLOG POST: High-quality, EEAT-friendly article in HTML format. 
                   - Use H1, H2, H3 tags.
                   - Use bullet points and bold text.
                   - Include an Amazon affiliate disclosure.
                   - Add 3 product recommendations as [[PRODUCT: Name]].
                4. IMAGE PROMPTS: Three detailed text-to-image prompts for this post.

                OUTPUT FORMAT:
                [TITLES]
                (List 3 titles)
                [TAGS]
                (Comma separated tags)
                [PROMPTS]
                (List 3 image prompts)
                [HTML]
                (The blog content)
                """

                response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
                full_text = response.text

                # --- PARSING RESULTS ---
                titles = re.search(r"\[TITLES\](.*?)\[TAGS\]", full_text, re.S).group(1).strip()
                tags = re.search(r"\[TAGS\](.*?)\[PROMPTS\]", full_text, re.S).group(1).strip()
                img_prompts = re.search(r"\[PROMPTS\](.*?)\[HTML\]", full_text, re.S).group(1).strip()
                blog_html = re.search(r"\[HTML\](.*)", full_text, re.S).group(1).strip()

                # --- PRODUCT LINK INJECTION ---
                found_products = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', blog_html)
                for p in found_products:
                    link = get_amazon_link(p, search_key, search_id, aff_id)
                    if link:
                        blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}" target="_blank" style="color: #FF9900; font-weight: bold;">{p} (View on Amazon)</a>')
                    else:
                        blog_html = blog_html.replace(f"[[PRODUCT: {p}]]", f"<strong>{p}</strong>")

                # --- DISPLAY ---
                st.success("✅ Content Generated Successfully!")
                
                tabs = st.tabs(["📄 Blog Preview", "📈 SEO & Metadata", "🎨 Image Prompts"])
                
                with tabs[0]:
                    st.markdown(blog_html, unsafe_allow_html=True)
                
                with tabs[1]:
                    st.subheader("SEO Friendly Titles")
                    st.code(titles)
                    st.subheader("SEO Tags")
                    st.code(tags)
                
                with tabs[2]:
                    st.subheader("Text-to-Image Prompts")
                    st.info("Copy these into Midjourney, Leonardo, or Canva AI.")
                    st.write(img_prompts)

                # --- DOWNLOAD ---
                final_output = f"\n\n{blog_html}"
                st.download_button(
                    label="💾 Download .html File",
                    data=final_output,
                    file_name="blog_post.html",
                    mime="text/html"
                )

            except Exception as e:
                st.error(f"Error: {e}")

