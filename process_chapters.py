# File: process_chapters.py

import json
import time
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

# --- This is our reliable "Worker" function, based on your original script ---
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
        
        # Wait for comments to load
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".space-y-0 > .py-4")))

        # Click "Load More Comments" button
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
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None # Return None on failure
    finally:
        driver.quit()
        
    print(f"Finished: {url} | Top comment likes: {highest_likes}")
    return {"comment": top_comment_text, "likes": highest_likes}


# --- Main execution block to orchestrate the scraping ---
if __name__ == "__main__":
    try:
        with open('chapter_list.json', 'r', encoding='utf-8') as f:
            manhwa_list = json.load(f)
    except FileNotFoundError:
        print("Error: chapter_list.json not found. Please run collect_urls.py first.")
        exit()

    # Create a flat list of all chapter URLs to process
    urls_to_scrape = []
    for manhwa in manhwa_list:
        urls_to_scrape.extend(manhwa['chapters'])

    print(f"Found {len(urls_to_scrape)} total chapters to scrape from {len(manhwa_list)} manhwa.")
    
    # --- CONCURRENCY SETUP ---
    # You can change this number depending on your computer's power.
    # 4 or 5 is a safe starting point.
    MAX_WORKERS = 5 
    
    results = []
    # Using ThreadPoolExecutor to run our scraper function in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # executor.map applies the function to every URL in the list
        # It automatically manages the threads for us.
        results = list(executor.map(scrape_chapter_comments, urls_to_scrape))
    
    # --- Process and Save the Final Results ---
    final_data = []
    result_index = 0
    for manhwa in manhwa_list:
        processed_chapters = []
        for chapter_url in manhwa['chapters']:
            result = results[result_index]
            if result:
                processed_chapters.append({
                    "url": chapter_url,
                    "top_comment": result['comment'],
                    "likes": result['likes']
                })
            result_index += 1
        
        final_data.append({
            "title": manhwa['title'],
            "processed_chapters": processed_chapters
        })

    # Save the final compiled data
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)
        
    print("\n✅ All scraping complete! Results have been saved to results.json")