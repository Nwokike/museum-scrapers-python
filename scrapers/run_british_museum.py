import os
import json
import shutil
import time
import requests
import urllib3
import pandas as pd
from tqdm import tqdm
from huggingface_hub import HfApi

# --- CONFIGURATION ---
REPO_ID = "nwokikeonyeka/british-museum-igbo-collection"
SOURCE_ID = "british_museum"
CSV_FILENAME = "british_museum.csv" # Expected input file name

# Output Directories
BASE_DIR = "data_british_museum"
DIRS = {
    "images": os.path.join(BASE_DIR, "images"),
    "clean": os.path.join(BASE_DIR, "clean")
}

# Disable SSL Warnings (British Museum media server has certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Browser Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def setup_directories():
    """Reset output directories."""
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)

def process_british_museum():
    """Reads CSV and downloads images."""
    
    # 1. Check for CSV
    if not os.path.exists(CSV_FILENAME):
        print(f"❌ Error: Could not find '{CSV_FILENAME}'.")
        print("   Please download the CSV from the British Museum search page and rename it.")
        return []

    print(f"📖 Reading {CSV_FILENAME}...")
    df = pd.read_csv(CSV_FILENAME)
    
    # Convert to list of dicts
    records = df.to_dict(orient='records')
    processed_data = []
    
    print(f"🔍 Found {len(records)} rows. Starting download...")
    
    for row in tqdm(records, desc="Processing"):
        # 1. Get Image URL
        img_url = row.get("Image")
        
        # Skip if invalid
        if not isinstance(img_url, str) or not img_url.startswith("http"):
            continue

        # 2. Extract Metadata
        museum_number = str(row.get("Museum number", "unknown")).strip()
        
        metadata = {
            "title": str(row.get("Title", "Untitled")),
            "idno": museum_number,
            "description": str(row.get("Description", "")),
            "object_type": str(row.get("Object type", "")),
            "production_date": str(row.get("Production date", "")),
            "materials": str(row.get("Materials", "")),
            "copyright": "© The Trustees of the British Museum"
        }

        # 3. Download Image
        try:
            # Create filename: bm_Af1934_01.jpg
            safe_id = museum_number.replace(".", "_").replace(" ", "_").replace("/", "-").replace(",", "")
            ext = img_url.split('.')[-1]
            filename = f"bm_{safe_id}.{ext}"
            filepath = os.path.join(DIRS["images"], filename)
            
            # Download (Ignoring SSL errors)
            if not os.path.exists(filepath):
                r = requests.get(img_url, headers=HEADERS, stream=True, timeout=15, verify=False)
                if r.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)
                else:
                    continue # Skip if download failed
            
            # 4. Add to dataset
            processed_data.append({
                "id": museum_number,
                "source_id": SOURCE_ID,
                "source_url": "https://www.britishmuseum.org/collection", 
                "metadata": metadata,
                "images": [
                    {"file_name": filename, "original_url": img_url}
                ]
            })
            
        except Exception as e:
            print(f"   Error on {museum_number}: {e}")

    return processed_data

def save_and_package(data):
    """Saves JSONL and packages files for upload."""
    if not data:
        print("No data collected.")
        return

    # 1. Save JSONL
    jsonl_path = os.path.join(DIRS["clean"], "data.jsonl")
    print(f"💾 Saving metadata to {jsonl_path}...")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
            
    # 2. Package Images (Move to clean/images/)
    final_images_dir = os.path.join(DIRS["clean"], "images")
    os.makedirs(final_images_dir, exist_ok=True)
    
    print("📦 Packaging images...")
    for item in data:
        for img in item["images"]:
            src = os.path.join(DIRS["images"], img["file_name"])
            dst = os.path.join(final_images_dir, img["file_name"])
            if os.path.exists(src):
                shutil.copy2(src, dst)

def upload_to_hf():
    """Uploads to Hugging Face."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("⚠️ HF_TOKEN not found. Skipping upload.")
        return

    print(f"☁️ Uploading to {REPO_ID}...")
    api = HfApi(token=token)
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)
    
    try:
        api.upload_folder(
            folder_path=DIRS["clean"],
            repo_id=REPO_ID,
            repo_type="dataset",
            path_in_repo=".",
            commit_message="Upload British Museum Collection"
        )
        print("🎉 Success! Dataset uploaded.")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    setup_directories()
    data = process_british_museum()
    if data:
        save_and_package(data)
        # upload_to_hf()
