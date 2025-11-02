
import os
import json
import requests
import re
import time
import shutil
import logging
from bs4 import BeautifulSoup
from tqdm.notebook import tqdm
from urllib.parse import urljoin
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from huggingface_hub import HfApi, create_repo

# --- 2. Configuration ---
BASE_URL = "https://jonesarchive.siu.edu/"
SOURCE_NAME = "G.I. Jones Archive (SIU)"
SOURCE_ID = "gijones" # for filenames
REPO_ID = "nwokikeonyeka/gi_jones_archive_dataset"
LOG_FILE = "gijones_scraper.log"

RAW_DIR = "data_jones_raw"
CLEAN_DIR = "data_jones_clean"
RAW_IMG_DIR = os.path.join(RAW_DIR, "images")
CLEAN_IMG_DIR = os.path.join(CLEAN_DIR, "images")
RAW_JSONL = os.path.join(RAW_DIR, "data.jsonl")
CLEAN_JSONL = os.path.join(CLEAN_DIR, "data.jsonl")
CLEAN_README = os.path.join(CLEAN_DIR, "README.md")
os.makedirs(RAW_IMG_DIR, exist_ok=True)
os.makedirs(CLEAN_IMG_DIR, exist_ok=True)

# --- 3. Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'), # 'w' to overwrite log
        logging.StreamHandler()
    ]
)

# This would be the main entry point if run as a script
def main():
    logging.info("--- Starting new G.I. Jones scrape ---")
    HF_TOKEN = input("Paste your Hugging Face WRITE token: ").strip()

    run_scraper()
    run_cleaner()
    create_readme()
    upload_to_hf(HF_TOKEN)

# --- 4. Scraper Functions (with Improvements) ---

def get_soup(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, timeout=20, headers=headers)
        r.raise_for_status()
        r.encoding = r.apparent_encoding 
        return BeautifulSoup(r.text, "html.parser")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to get soup for {url}: {e}")
        return None

def sanitize_filename(name):
    name = name.lower().replace(" ", "-")
    name = re.sub(r'[^\w\s.-]', '', name) # Allow dots
    name = re.sub(r'--+', '-', name)
    return name[:100]

def get_all_category_pages(base_url):
    logging.info("Finding all categories from 'photo-indexes/' page...")
    category_pages = set()
    index_page_url = urljoin(base_url, "photo-indexes/")
    
    soup = get_soup(index_page_url)
    if not soup:
        logging.critical("Failed to load photo-indexes/, cannot find categories.")
        return []

    exclude_list = ["/jones-biography/", "/bibliography/"]
    
    for a in soup.find_all("a", href=True):
        href = a['href']
        full_link = urljoin(index_page_url, href)
        link_text = a.text.strip()
        
        if ("siu.edu" in full_link and 
            href.endswith('/') and 
            link_text and
            full_link != index_page_url and
            not any(ex in full_link for ex in exclude_list)):
             category_pages.add(full_link)
    
    logging.info(f"Found {len(category_pages)} categories.")
    return list(category_pages)

def download_image(img_url):
    try:
        r = requests.get(img_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        data = r.content
        
        original_filename = os.path.basename(img_url.split("?")[0])
        safe_filename = sanitize_filename(original_filename)
        new_filename = f"{SOURCE_ID}_{safe_filename}"
        
        save_path = os.path.join(RAW_IMG_DIR, new_filename)
        with open(save_path, "wb") as f:
            f.write(data)
            
        with Image.open(save_path) as img:
            width, height = img.size
        file_size = os.path.getsize(save_path)
            
        return (new_filename, width, height, file_size)
    except Exception as e:
        logging.warning(f"Failed to download image {img_url}: {e}")
        return None

def scrape_gallery_page(url):
    soup = get_soup(url)
    if soup is None: return []

    all_post_data = []
    gallery_items = soup.select(".et_pb_gallery_item")
    
    if not gallery_items:
        logging.warning(f"No gallery items found on {url}")
        return []
    
    for item in gallery_items:
        img_link_tag = item.select_one(".et_pb_gallery_image a[href]")
        caption_tag = item.select_one(".et_pb_gallery_caption")
        
        if not img_link_tag:
            continue

        full_image_url = img_link_tag['href']
        caption = caption_tag.get_text(strip=True) if caption_tag else "Untitled"
        title = caption
        
        img_stats = download_image(full_image_url)
        
        if img_stats:
            new_filename, width, height, file_size = img_stats
            
            scraped_images = [{
                "file_name": new_filename,
                "original_url": full_image_url,
                "raw_caption": caption,
                "width": width,
                "height": height,
                "file_size_bytes": file_size
            }]

            post_data = {
                "id": f"{SOURCE_ID}_{sanitize_filename(full_image_url)}",
                "source_name": SOURCE_NAME,
                "source_type": "primary",
                "original_url": url, 
                "title": title,
                "raw_content": caption,
                "images": scraped_images,
                "tags_scraped": [],
                "license_info": "© G.I. Jones Estate (Handled by MAA Cambridge)",
                "timestamp_scraped": datetime.now().isoformat(),
                "source_specific_metadata": {"source_id": SOURCE_ID, "gallery_page": url}
            }
            all_post_data.append(post_data)
    return all_post_data

def run_scraper():
    logging.info(f"--- [PART 1/4] Starting scrape of {BASE_URL} ---")
    category_pages_to_scrape = get_all_category_pages(BASE_URL)
    logging.info(f"Found {len(category_pages_to_scrape)} category pages.")

    with open(RAW_JSONL, "w", encoding="utf-8") as f:
        for url in tqdm(category_pages_to_scrape, desc="Scraping category pages"):
            try:
                all_data_from_page = scrape_gallery_page(url)
                for data in all_data_from_page:
                    if data and data['images']:
                        f.write(json.dumps(data) + "
")
                time.sleep(1) # Politeness delay
            except Exception as e:
                logging.error(f"❌ Failed to scrape or save page {url}: {e}")
    logging.info("✅ Scraper run complete.")

def run_cleaner():
    logging.info("--- [PART 2/4] Cleaning the data ---")
    good_images = set()
    bad_images_count = 0
    image_files = os.listdir(RAW_IMG_DIR)
    for filename in tqdm(image_files, desc="Validating images"):
        source_path = os.path.join(RAW_IMG_DIR, filename)
        clean_path = os.path.join(CLEAN_IMG_DIR, filename)
        try:
            with Image.open(source_path) as img:
                img.verify()
            shutil.copy(source_path, clean_path)
            good_images.add(filename)
        except Exception as e:
            logging.warning(f"Skipping bad image {filename}: {e}")
            bad_images_count += 1
    logging.info(f"Found and skipped {bad_images_count} bad images.")

    clean_lines = 0
    with open(RAW_JSONL, "r", encoding="utf-8") as f_in,          open(CLEAN_JSONL, "w", encoding="utf-8") as f_out:
        for line in f_in:
            data = json.loads(line)
            if not any(img['file_name'] in good_images for img in data['images']):
                continue
            f_out.write(json.dumps(data) + "
")
            clean_lines += 1
    logging.info(f"Wrote {clean_lines} clean lines to {CLEAN_JSONL}.")
    logging.info("✅ Cleaning complete.")

def create_readme():
    logging.info("--- [PART 3/4] Creating placeholder README.md ---")
    readme_content = f"""---
license: other
---
# G.I. Jones Photographic Archive (SIU)
This dataset is a raw scrape of the G.I. Jones Photographic Archive, hosted by Southern Illinois University (SIU) at `{BASE_URL}`.
**This is a placeholder README.md. Full metadata will be added later.**
"""
    with open(CLEAN_README, "w", encoding="utf-8") as f:
        f.write(readme_content)
    logging.info("✅ Placeholder README.md created.")

def upload_to_hf(token):
    logging.info("--- [PART 4/4] Uploading to Hugging Face ---")
    logging.info(f"Preparing to upload {CLEAN_DIR} to {REPO_ID}...")
    for attempt in range(3):
        try:
            api = HfApi(token=token)
            create_repo(REPO_ID, repo_type="dataset", token=token, exist_ok=True)
            api.upload_folder(
                folder_path=CLEAN_DIR,
                repo_id=REPO_ID,
                repo_type="dataset",
            )
            logging.info("="*50)
            logging.info("✅✅✅ G.I. JONES SCRAPE COMPLETE! ✅✅✅")
            logging.info(f"Your new dataset is now live at:")
            logging.info(f"https://huggingface.co/datasets/{REPO_ID}")
            logging.info("="*50)
            break
        except Exception as e:
            logging.error(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                logging.info("Retrying in 10 seconds...")
                time.sleep(10)
            else:
                logging.critical("All upload attempts failed.")

if __name__ == "__main__":
    HF_TOKEN_ENV = os.environ.get("HF_TOKEN")
    if HF_TOKEN_ENV:
        main()
    else:
        print("This script is intended to be run from a command line with HF_TOKEN set.")
        print("Or by calling the functions directly in a notebook.")
