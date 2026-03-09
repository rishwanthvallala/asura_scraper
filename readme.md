# Asura Scraper & Manhwa Popularity Analyzer

This project is a web scraping tool designed to collect data from `asuracomic.net` to analyze the popularity of various manhwa series. It operates by scraping the latest chapters of all available series, identifying the top-rated user comment (by likes) for each, and then ranking the series based on this metric.

The core idea is that the comment with the most likes on a recent chapter can serve as a proxy for reader engagement and overall popularity.

---

## Features

-   **Comprehensive URL Collection**: Navigates through paginated listings to gather titles and the latest three chapter URLs for every manhwa on the site.
-   **Dynamic Content Handling**: Uses Selenium to manage JavaScript-rendered content, including clicking "Load More Comments" buttons to ensure all comments are accessible.
-   **Persistent Browser Sessions**: Reuses a fixed pool of browser instances across all URLs — dramatically faster than launching a new browser per request.
-   **Resilient Scraping**: Auto-retries failed URLs up to 2 times before skipping. Handles `StaleElementReferenceException` by re-fetching elements by index.
-   **Resume Support**: On re-run, `process_chapters.py` loads any existing `results.json` and skips already-scraped URLs — no data is lost if the script crashes mid-way.
-   **Incremental Saves**: Writes results to disk after every successful URL, so a crash never loses more than the currently in-flight batch.
-   **Popularity Ranking**: Aggregates the collected data, finds the highest like count for each series' recent chapters, and generates a formatted, ranked table of the top 50 most popular manhwa.

---

## Project Structure

```
asura_scraper/
│
├── collect_urls.py         # Step 1: Scrapes all manhwa titles and chapter URLs.
├── process_chapters.py     # Step 2: Scrapes each chapter URL for the top comment.
├── rank.py                 # Step 3: Analyzes the results and prints a ranked table.
│
├── chapter_list.json       # Output of collect_urls.py
├── results.json            # Output of process_chapters.py
├── fill_gaps.py            # (Deprecated) Superseded by process_chapters.py resume support.
└── scrape.py               # A utility script for testing the scraping logic on a single URL.
```

### File Descriptions

-   `collect_urls.py`: The first script to run. It launches a headless browser, navigates through the manhwa listing pages, and saves all titles and their latest chapter URLs into `chapter_list.json`.
-   `process_chapters.py`: The main data processing script. It reads `chapter_list.json`, then concurrently scrapes each chapter URL using a pool of persistent browser sessions. It automatically resumes from where it left off if interrupted — just run it again and it will only scrape what's missing. Results are saved to `results.json`.
-   `rank.py`: The final script in the workflow. It reads `results.json`, calculates the peak like count for each series, and prints a clean, ranked table of the top 50 series to the console.
-   `scrape.py`: A simple testing script to debug or verify the scraping logic for a single chapter URL without running the entire project.
-   `fill_gaps.py`: Deprecated. Its functionality is now built into `process_chapters.py`.
-   `chapter_list.json`: A JSON file containing an array of all manhwa, with their titles and a list of the last three chapter URLs.
-   `results.json`: The final dataset. It mirrors the structure of the chapter list but includes the scraped top comment and its like count for each successfully processed chapter.

---

## How to Use

### Prerequisites

-   Python 3.x
-   Selenium
-   Tabulate
-   A compatible web driver (e.g., ChromeDriver) installed and accessible in your system's PATH.

Install the required Python libraries with pip:
```bash
pip install selenium tabulate
```

### Execution Workflow

**Step 1: Collect All Chapter URLs**
```bash
python collect_urls.py
```
Generates `chapter_list.json` with all manhwa titles and their latest 3 chapter URLs.

**Step 2: Scrape Comments**
```bash
python process_chapters.py
```
Scrapes all chapter URLs for top comments and saves to `results.json`. If interrupted, just run it again — it will resume from where it left off, skipping already-scraped URLs.

**Step 3: Rank the Results**
```bash
python rank.py
```
Reads `results.json` and prints a ranked table of the top 50 manhwa by peak comment likes.

### Example Output from `rank.py`

```
--- Top 50 Manhwa by Peak Comment Likes ---
+========+=======================================+=========================================+
|   Rank | Manhwa Title                          |   Highest Like Count in Recent Chapters |
+========+=======================================+=========================================+
|      1 | The Greatest Estate Developer         |                                    2310 |
|      2 | The Regressed Mercenary's Mach...     |                                    1721 |
|      3 | The Extra's Academy Survival G...     |                                    1298 |
|      4 | Eternally Regressing Knight           |                                    1332 |
|      5 | Absolute Regression                   |                                    1070 |
|    ... | ...                                   |                                     ... |
+========+=======================================+=========================================+
```

---

## Disclaimer

This project is intended for educational purposes only. Web scraping can be resource-intensive for the target website. Please use this tool responsibly and be mindful of the website's terms of service.
