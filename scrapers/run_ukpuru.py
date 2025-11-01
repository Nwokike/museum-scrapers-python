
import os
import json
import requests
import re
import time
import shutil
from bs4 import BeautifulSoup
from tqdm.notebook import tqdm
from urllib.parse import urljoin
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from huggingface_hub import HfApi, create_repo

# --- Configuration ---
BASE_URL = "https://blog.ukpuru.org"
SOURCE_NAME = "Ukpuru Blog"
SOURCE_ID = "ukpuru"

RAW_DIR = "data_raw"
CLEAN_DIR = "data_clean"

RAW_IMG_DIR = os.path.join(RAW_DIR, "images")
CLEAN_IMG_DIR = os.path.join(CLEAN_DIR, "images")
RAW_JSONL = os.path.join(RAW_DIR, "data.jsonl")
CLEAN_JSONL = os.path.join(CLEAN_DIR, "data.jsonl")
CLEAN_README = os.path.join(CLEAN_DIR, "README.md")

# --- Helper Functions ---
def get_soup(url):
    try:
        headers = {'User-Agent': 'IgboArchives-ScraperBot/1.0'}
        r = requests.get(url, params={'m': '0'}, timeout=20, headers=headers)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.exceptions.RequestException:
        return None

def sanitize_filename(name):
    name = name.lower().replace(" ", "-")
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'--+', '-', name)
    return name[:100]

def get_all_posts(base_url):
    posts = []
    current_url = base_url
    pbar = tqdm(desc="Finding all post pages")
    while current_url:
        soup = get_soup(current_url)
        if soup is None: break
        links = [a["href"] for a in soup.select("h3.post-title a")]
        if not links: break
        posts.extend(links)
        pbar.update(1)
        older_posts_link = soup.select_one("a.blog-pager-older-link")
        if older_posts_link and older_posts_link.get('href'):
            current_url = urljoin(base_url, older_posts_link['href'])
            time.sleep(0.2)
        else:
            current_url = None
    pbar.close()
    return list(dict.fromkeys(posts))

def download_image(img_url, post_slug, index):
    try:
        img_url = urljoin(BASE_URL, img_url)
        data = requests.get(img_url, timeout=15, headers={'User-Agent': 'IgboArchives-ScraperBot/1.0'}).content
        ext = os.path.splitext(img_url.split("?")[0])[-1].lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']: ext = ".jpg"
        new_filename = f"{SOURCE_ID}_{post_slug}_{index:02d}{ext}"
        save_path = os.path.join(RAW_IMG_DIR, new_filename)
        with open(save_path, "wb") as f: f.write(data)
        return new_filename
    except Exception:
        return None

def scrape_post_data(url):
    soup = get_soup(url)
    if soup is None: return None
    title_tag = soup.select_one("h1.post-title") or soup.select_one("h3.post-title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    post_slug = sanitize_filename(title)
    content_div = soup.select_one("div.post-body")
    if not content_div: return None
    raw_text_content = content_div.get_text("
", strip=True)
    scraped_images = []
    for i, img_tag in enumerate(content_div.select("img")):
        img_src = img_tag.get('src')
        if not img_src: continue
        caption = None
        figure_parent = img_tag.find_parent("figure")
        if figure_parent:
            caption_tag = figure_parent.find("figcaption")
            caption = caption_tag.get_text(strip=True) if caption_tag else None
        elif img_tag.find_next_sibling("p", class_="wp-caption-text"):
            caption = img_tag.find_next_sibling("p", class_="wp-caption-text").get_text(strip=True)
        new_filename = download_image(img_src, post_slug, i)
        if new_filename:
            scraped_images.append({
                "file_name": new_filename,
                "original_url": urljoin(BASE_URL, img_src),
                "raw_caption": caption
            })
    tags = [a.get_text(strip=True) for a in soup.select("a[rel='tag']")]
    post_data = {
        "id": f"{SOURCE_ID}_{sanitize_filename(url)}",
        "source_name": SOURCE_NAME, "source_type": "secondary",
        "original_url": url, "title": title, "raw_content": raw_text_content,
        "images": scraped_images, "tags_scraped": tags,
        "license_info": f"© {SOURCE_NAME} (Assumed)",
        "timestamp_scraped": datetime.now().isoformat(),
        "source_specific_metadata": {}
    }
    return post_data

def run_scraper():
    print(f"--- [PART 1/3] Starting scrape of {BASE_URL} ---")
    os.makedirs(RAW_IMG_DIR, exist_ok=True)
    posts_to_scrape = get_all_posts(BASE_URL)
    print(f"Found {len(posts_to_scrape)} total posts.")
    with open(RAW_JSONL, "w", encoding="utf-8") as f:
        for url in tqdm(posts_to_scrape, desc="Scraping new posts"):
            try:
                data = scrape_post_data(url)
                if data: f.write(json.dumps(data) + "
")
            except Exception as e:
                print(f"❌ Failed to scrape or save {url}: {e}")
    print("✅ Scraper run complete.")

def run_cleaner():
    print(f"
--- [PART 2/3] Cleaning the data ---")
    os.makedirs(CLEAN_IMG_DIR, exist_ok=True)
    good_images = set()
    bad_images_count = 0
    image_files = os.listdir(RAW_IMG_DIR)
    for filename in tqdm(image_files, desc="Validating images"):
        source_path = os.path.join(RAW_IMG_DIR, filename)
        clean_path = os.path.join(CLEAN_IMG_DIR, filename)
        try:
            with Image.open(source_path) as img: img.verify()
            shutil.copy(source_path, clean_path)
            good_images.add(filename)
        except Exception:
            bad_images_count += 1
    print(f"Found and skipped {bad_images_count} bad images.")
    
    clean_lines = 0
    with open(RAW_JSONL, "r", encoding="utf-8") as f_in,          open(CLEAN_JSONL, "w", encoding="utf-8") as f_out:
        for line in f_in:
            data = json.loads(line)
            data['images'] = [img for img in data['images'] if img['file_name'] in good_images]
            f_out.write(json.dumps(data) + "
")
            clean_lines += 1
    print(f"Wrote {clean_lines} clean lines to {CLEAN_JSONL}.")
    print("✅ Cleaning complete.")

def create_readme():
    print(f"
--- [PART 3/3] Creating README.md ---")
    # (Here you would add the full README content)
    readme_content = "This folder contains the clean data."
    with open(os.path.join(CLEAN_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✅ README.md created.")

if __name__ == "__main__":
    run_scraper()
    run_cleaner()
    create_readme()
    print("
--- Process Finished ---")
    print(f"Clean data is ready in {CLEAN_DIR}")
