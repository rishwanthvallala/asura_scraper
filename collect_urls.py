# File: collect_urls.py (The Correct Selenium Version)

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_all_chapter_urls_selenium():
    """
    Uses Selenium to reliably scrape the paginated listings, which are loaded
    by JavaScript, and collects all manhwa titles and latest chapter URLs.
    """
    domain = "https://asuracomic.net"
    base_url = f"{domain}/page/{{}}"
    all_manhwa_data = []

    print("Launching headless browser for URL collection...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
    options.add_argument('--log-level=3')
    
    service = webdriver.ChromeService()
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # Loop through pages 1 to 7 to be safe.
        for page_num in range(1, 8):
            url = base_url.format(page_num)
            print(f"Navigating to page: {url}")
            driver.get(url)

            try:
                # Wait for the main list container to be present.
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.grid.grid-rows-1.grid-cols-1")))
                time.sleep(2) # Extra wait for all items to render

                # Find all the individual manhwa blocks.
                manhwa_blocks = driver.find_elements(By.XPATH, "//div[contains(@class, 'grid-cols-12') and contains(@class, 'm-2')]")
                
                if not manhwa_blocks:
                    print(f"No more manhwa found on page {page_num}. Stopping.")
                    break
                
                print(f"Found {len(manhwa_blocks)} manhwa on this page.")

                for block in manhwa_blocks:
                    try:
                        title_element = block.find_element(By.CSS_SELECTOR, "span.text-\\[15px\\].font-medium a")
                        title = title_element.text.strip()
                        
                        chapter_elements = block.find_elements(By.CSS_SELECTOR, "div.flex-col a")
                        latest_three_chapters = [el.get_attribute('href') for el in chapter_elements[:3]]

                        if title and latest_three_chapters:
                            all_manhwa_data.append({
                                "title": title,
                                "chapters": latest_three_chapters
                            })
                    except NoSuchElementException:
                        # Skip if a block is not structured as expected (e.g., an ad)
                        continue

            except TimeoutException:
                print(f"Timed out waiting for content on page {page_num}. Stopping.")
                break
            except Exception as e:
                print(f"Could not process page {page_num}. Error: {e}")
                continue

    finally:
        driver.quit()
        print("Browser closed.")
            
    return all_manhwa_data

if __name__ == "__main__":
    manhwa_list = get_all_chapter_urls_selenium()
    
    if manhwa_list:
        print(f"\nSuccessfully collected data for {len(manhwa_list)} manhwa.")
        
        # Save the collected data to a JSON file for the next step.
        with open('chapter_list.json', 'w', encoding='utf-8') as f:
            json.dump(manhwa_list, f, indent=4)
        print("\n✅ Saved all collected URLs to chapter_list.json")
    else:
        print("\nNo data was collected. The script failed to find any manhwa blocks.")