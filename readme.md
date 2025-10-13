# Asura Scraper & Manhwa Popularity Analyzer

**Generation Date:** 2025-10-13 11:51:38

This project is a web scraping tool designed to collect data from `asuracomic.net` to analyze the popularity of various manhwa series. It operates by scraping the latest chapters of all available series, identifying the top-rated user comment (by likes) for each, and then ranking the series based on this metric.

The core idea is that the comment with the most likes on a recent chapter can serve as a proxy for reader engagement and overall popularity.

---

## Features

-   **Comprehensive URL Collection**: Navigates through paginated listings to gather titles and the latest three chapter URLs for every manhwa on the site.
-   **Dynamic Content Handling**: Uses Selenium to manage JavaScript-rendered content, including clicking "Load More Comments" buttons to ensure all comments are accessible.
-   **Concurrent Scraping**: Employs a `ThreadPoolExecutor` to process multiple chapter URLs simultaneously, significantly speeding up the data collection process.
-   **Resilient Scraping**: Includes a `fill_gaps.py` script to identify and re-scrape any chapters that may have failed during the initial run, ensuring data completeness.
-   **Popularity Ranking**: Aggregates the collected data, finds the highest like count for each series' recent chapters, and generates a formatted, ranked table of the top 50 most popular manhwa.

---

## Project Structure

The project is organized into several Python scripts and JSON data files, each with a specific role in the workflow.

```
asura_scraper/
│
├── collect_urls.py         # Step 1: Scrapes all manhwa titles and chapter URLs.
├── process_chapters.py     # Step 2: Scrapes each chapter URL for the top comment.
├── fill_gaps.py            # (Optional) Step 3: Re-scrapes any failed URLs.
├── rank.py                 # Step 4: Analyzes the results and prints a ranked table.
│
├── chapter_list.json       # Output of collect_urls.py
├── results.json            # Final output of process_chapters.py
└── scrape.py               # A utility script for testing the scraping logic on a single URL.
```

### File Descriptions

-   `collect_urls.py`: The first script to run. It launches a headless browser, navigates through the manhwa listing pages, and saves all titles and their latest chapter URLs into `chapter_list.json`.
-   `process_chapters.py`: The main data processing script. It reads `chapter_list.json`, then concurrently scrapes each chapter URL to find the comment with the most likes. The results are compiled and saved into `results.json`.
-   `fill_gaps.py`: An optional utility script. If `process_chapters.py` fails on some URLs, this script compares `chapter_list.json` with `results.json` to find the missing chapters and attempts to scrape them again, merging the new data into `results.json`.
-   `rank.py`: The final script in the workflow. It reads `results.json`, calculates the peak like count for each series, and prints a clean, ranked table of the top 50 series to the console.
-   `scrape.py`: A simple testing script to debug or verify the scraping logic for a single chapter URL without running the entire project.
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

The scripts are designed to be run in a specific order to complete the analysis.

**Step 1: Collect All Chapter URLs**
Run `collect_urls.py` to create the initial list of chapters to be scraped.

```bash
python collect_urls.py
```
This will generate the `chapter_list.json` file.

**Step 2: Process Chapters and Scrape Comments**
Run `process_chapters.py` to scrape the URLs from the generated JSON file. This is the most time-consuming step.

```bash
python process_chapters.py
```
This will create the `results.json` file containing the scraped data.

**Step 3 (Optional): Fill Gaps from Failed Attempts**
If you noticed errors during Step 2, run this script to attempt to fill in any missing data points.

```bash
python fill_gaps.py
```

**Step 4: Rank the Results**
Finally, run `rank.py` to analyze the collected data and view the popularity rankings.

```bash
python rank.py
```
This will display a formatted table in your console showing the top 50 manhwa ranked by the highest number of likes on a recent chapter's top comment.

### Example Output from `rank.py`

```
--- Top 50 Manhwa by Peak Comment Likes ---
+========+=======================================+=======================================+
|   Rank | Manhwa Title                          |   Highest Like Count in Recent Chapters |
+========+=======================================+=======================================+
|      1 | The Greatest Estate Developer         |                                    2310 |
|      2 | The Regressed Mercenary's Mach...     |                                    1721 |
|      3 | The Extra’s Academy Survival G...     |                                    1298 |
|      4 | Eternally Regressing Knight           |                                    1332 |
|      5 | Absolute Regression                   |                                    1070 |
|    ... | ...                                   |                                     ... |
+========+=======================================+=======================================+
```
---

## Disclaimer

This project is intended for educational purposes only. Web scraping can be resource-intensive for the target website. Please use this tool responsibly and be mindful of the website's terms of service.
