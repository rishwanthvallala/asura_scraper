# File: fill_gaps.py

import json
import time
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

# This is the exact same reliable "worker" function from the previous script.
def scrape_chapter_comments(url):
    """
    Scrapes a single chapter URL for its top comment using Selenium.
    This function is designed to be run in parallel by multiple threads.
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    options.add_argument('--log-level=3')
    
    service = webdriver.ChromeService()
    driver = webdriver.Chrome(service=service, options=options)
    
    highest_likes = -1
    top_comment_text = ""

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".space-y-0 > .py-4")))

        while True:
            try:
                load_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Load More Comments')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                load_more_button.click()
                time.sleep(2)
            except (NoSuchElementException, ElementClickInterceptedException):
                break

        comments = driver.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4")
        
        for comment in comments:
            try:
                like_button = comment.find_element(By.CSS_SELECTOR, "button[data-tooltip-content='Login to like this comment']")
                like_count_element = like_button.find_element(By.TAG_NAME, "span")
                current_likes = int(like_count_element.text)

                if current_likes > highest_likes:
                    highest_likes = current_likes
                    comment_text_element = comment.find_element(By.CSS_SELECTOR, ".prose p")
                    top_comment_text = comment_text_element.text
            except (NoSuchElementException, ValueError):
                continue
    
    except Exception:
        # On any error, we return None so we know it failed.
        print(f"Error scraping {url}, will retry later.")
        return None
    finally:
        driver.quit()
        
    print(f"Finished: {url} | Top comment likes: {highest_likes}")
    return {"url": url, "top_comment": top_comment_text, "likes": highest_likes}

if __name__ == "__main__":
    # --- Step 1: Load both files ---
    try:
        with open('chapter_list.json', 'r', encoding='utf-8') as f:
            master_list = json.load(f)
        with open('results.json', 'r', encoding='utf-8') as f:
            current_results = json.load(f)
    except FileNotFoundError:
        print("Error: Make sure both chapter_list.json and results.json are in this directory.")
        exit()

    # --- Step 2: Identify the missing URLs ---
    # First, create a set of all URLs that have already been successfully scraped.
    scraped_urls = set()
    for manhwa in current_results:
        for chapter in manhwa.get("processed_chapters", []):
            scraped_urls.add(chapter["url"])

    # Now, find which URLs from the master list are missing from our results.
    urls_to_retry = []
    for manhwa in master_list:
        for chapter_url in manhwa["chapters"]:
            if chapter_url not in scraped_urls:
                urls_to_retry.append(chapter_url)

    if not urls_to_retry:
        print("✅ No missing chapters found. Your results.json file is complete!")
        exit()

    print(f"Found {len(urls_to_retry)} missing chapters. Starting to re-scrape...")

    # --- Step 3: Re-scrape only the missing URLs ---
    MAX_WORKERS = 5
    newly_scraped_results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Filter out None results for chapters that failed again
        newly_scraped_results = [res for res in executor.map(scrape_chapter_comments, urls_to_retry) if res is not None]

    if not newly_scraped_results:
        print("\nCould not scrape any of the missing chapters. They may still be failing.")
        exit()
        
    print(f"\nSuccessfully scraped {len(newly_scraped_results)} new chapters.")
        
    # --- Step 4: Merge the new data with the old data ---
    # Create a lookup map of the new results for easy access
    new_results_map = {result['url']: result for result in newly_scraped_results}
    
    # Create a lookup map of the old results
    old_results_map = {
        chap['url']: chap for man in current_results 
        for chap in man.get('processed_chapters', [])
    }
    
    # Combine the old and new maps. If a URL is in both, the new one will overwrite it.
    combined_results_map = {**old_results_map, **new_results_map}

    # Rebuild the final JSON file from the master list to preserve the structure
    final_data = []
    for manhwa in master_list:
        processed_chapters = []
        for chapter_url in manhwa["chapters"]:
            if chapter_url in combined_results_map:
                # Add the data, but remove the URL from the nested dict to avoid redundancy
                chapter_data = combined_results_map[chapter_url]
                processed_chapters.append({
                    "url": chapter_url,
                    "top_comment": chapter_data['top_comment'],
                    "likes": chapter_data['likes']
                })
        
        if processed_chapters:
            final_data.append({
                "title": manhwa['title'],
                "processed_chapters": processed_chapters
            })

    # --- Step 5: Overwrite the old results file with the complete data ---
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)
        
    print("\n✅ All gaps filled! results.json has been updated and is now more complete.")
    