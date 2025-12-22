import streamlit as st
import requests
import re
import os
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Affiliate Content Master", layout="wide")
st.title("🚀 One-Click Affiliate Content Creator")

# Sidebar for Free API Keys
with st.sidebar:
    st.header("🔑 API Setup (Free Tier)")
    gemini_key = st.text_input("Gemini API Key", type="password")
    search_key = st.text_input("Google Search API Key", type="password")
    search_id = st.text_input("Search Engine ID (CX)", type="password")
    affiliate_id = st.text_input("Amazon Associate ID", value="mytag-20")

# --- CORE FUNCTIONS ---

def get_free_amazon_link(product_name):
    """Searches Amazon for a product using Google's 100-free-per-day API."""
    search_url = f"https://www.googleapis.com/customsearch/v1?q=site:amazon.com {product_name}&key={search_key}&cx={search_id}"
    try:
        res = requests.get(search_url).json()
        raw_url = res['items'][0]['link']
        asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', raw_url)
        if asin_match:
            return f"https://www.amazon.com/dp/{asin_match.group(1)}/?tag={affiliate_id}"
    except: return None

def process_content(text_input, url_input, title, keywords):
    client = genai.Client(api_key=gemini_key)
    
    # 1. Gather Source Text
    source_text = text_input
    if url_input:
        res = requests.get(url_input, headers={'User-Agent': 'Mozilla/5.0'})
        source_text = BeautifulSoup(res.text, 'html.parser').get_text()[:5000]

    # 2. Research & Rewrite (Gemini)
    prompt = f"Rewrite this into an SEO blog post. Title: {title}. Keywords: {keywords}. Format in clean HTML body only. Add exactly 3 [[PRODUCT: name]] placeholders where relevant."
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    draft_html = response.text

    # 3. Generate Image (Imagen 3 - Free in Gemini API)
    img_resp = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt=f"Professional blog hero image for: {title}",
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    img_data = img_resp.generated_images[0].image
    
    # 4. Final Polish & Saving
    folder = title.replace(" ", "_").lower()[:20]
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/hero.png", "wb") as f: f.write(img_data)
    
    # Replace placeholders with real links
    products = re.findall(r'\[\[PRODUCT:\s*(.*?)\]\]', draft_html)
    for p in products:
        link = get_free_amazon_link(p)
        if link:
            draft_html = draft_html.replace(f"[[PRODUCT: {p}]]", f'<a href="{link}"><strong>{p}</strong></a>')

    final_html = f'<img src="hero.png" width="100%"><br>' + draft_html
    with open(f"{folder}/index.html", "w") as f: f.write(final_html)
    return final_html, folder

# --- UI LAYOUT ---
col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Choose Input Type", ["URL Scraper", "Manual Text Input"])
    u_input = st.text_input("URL") if mode == "URL Scraper" else None
    t_input = st.text_area("Paste your blog here") if mode == "Manual Text Input" else None

with col2:
    target_title = st.text_input("New SEO Title")
    target_keys = st.text_input("Target Keywords (comma separated)")

if st.button("🚀 Run One-Click Research & Write"):
    if not (gemini_key and search_key):
        st.error("Please provide your free API keys in the sidebar.")
    else:
        with st.spinner("Researching, Generating Image, and Writing..."):
            html_out, folder_name = process_content(t_input, u_input, target_title, target_keys)
            st.success(f"Saved to folder: {folder_name}")
            st.markdown(html_out, unsafe_allow_value=True)
