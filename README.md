# 🏛️ Museum Scrapers (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-enabled-green)](https://playwright.dev/)

**A modular collection of professional Python scripts for extracting high-quality data from digital museum archives and cultural heritage collections.**

This repository serves as an educational resource and a toolkit for **Digital Humanities** researchers, developers, and archivists. It demonstrates modern scraping patterns including:
* **Dynamic Scraping:** Using `Playwright` to handle JavaScript-heavy museum viewers.
* **IIIF Integration:** Extracting maximum-resolution images directly from IIIF servers (bypassing web thumbnails).
* **Metadata Normalization:** converting messy museum HTML into structured JSONL datasets.
* **Async Concurrency:** Fast, non-blocking downloads using `asyncio`.

---

## 📂 Supported Institutions

Each script is a standalone tool targeting a specific digital archive architecture.

| Institution | Script | Tech Stack | Key Features |
| :--- | :--- | :--- | :--- |
| **Pitt Rivers Museum** | `scrapers/run_pitt_rivers.py` | `Playwright`, `AsyncIO` | • **IIIF Max-Res Extraction**<br>• Bypasses "Sensitive Content" popups<br>• Hybrid Search + Scraping |
| **British Museum** | `scrapers/run_british_museum.py` | `Pandas`, `Requests` | • **CSV-driven extraction**<br>• Handles "Preview" quality access<br>• Metadata mapping |
| **MAA Cambridge** | `scrapers/run_maa_cambridge.py` | `Playwright` | • **Dynamic JS Navigation**<br>• Deep metadata (Context, Photographer)<br>• Multi-view image linking |
| **G.I. Jones Archive** | `scrapers/run_gijones.py` | `BeautifulSoup` | • Static site traversing<br>• Gallery iteration |
| **Ukpuru Blog** | `scrapers/run_ukpuru.py` | `BeautifulSoup` | • Blogspot/Blogger parsing<br>• Unstructured text extraction |

---

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Nwokike/museum-scrapers-python.git
cd museum-scrapers-python

```

### 2. Install Dependencies

This project relies on `playwright` for dynamic sites and `pandas` for data handling.

```bash
pip install -r requirements.txt

```

### 3. Install Browser Engines

Required for the MAA and Pitt Rivers scrapers.

```bash
playwright install chromium

```

---

## 📖 Usage Examples

Each scraper is designed to be run independently.

### Example 1: Scraping the Pitt Rivers Museum

This script navigates the search results for a specific query (e.g., "Igbo") and extracts high-res IIIF images.

```bash
python scrapers/run_pitt_rivers.py

```

*Output:* Creates a `data_pitt_rivers/` folder with `images/` and `data.jsonl`.

### Example 2: Processing British Museum Data

Place your CSV export (`british_museum.csv`) in the folder before running.

```bash
python scrapers/run_british_museum.py

```

---

## ⚖️ Ethics & Legal Disclaimer

**Please scrape responsibly.**

1. **Respect Rate Limits:** These scripts are powerful. Do not overwhelm museum servers. Use `time.sleep()` intervals (included in scripts) to be a polite bot.
2. **Copyright:**
* **The Code:** This repository is open source (MIT License). You can use the *code* freely.
* **The Data:** The *content* you scrape (images, text) is subject to the copyright terms of the respective institutions (e.g., "© Trustees of the British Museum", "CC BY-NC-ND 4.0").


3. **Usage:** This tool is for **educational and research purposes**. Do not use scraped data for commercial products without obtaining proper licenses from the source institutions.

---

## 🤝 Contributing

We welcome contributions! If you have built a scraper for another museum (e.g., The Met, Smithsonian, Quai Branly), please submit a Pull Request.

1. Fork the repo.
2. Create your scraper in `scrapers/run_NEW_SOURCE.py`.
3. Ensure it outputs structured `JSONL` and separates images into an `/images` folder.

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
