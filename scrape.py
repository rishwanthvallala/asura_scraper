# Save this code. This is the confirmed working version.

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

def get_top_comment_from_page(url):
    """
    Scrapes a chapter URL for the top comment by directly interacting with the page
    using Selenium. This is the proven, reliable method.
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
        print(f"Navigating to {url}...")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # --- Wait for the first comment to be visible (The Proven Wait Condition) ---
        print("Waiting for comments section to load...")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".space-y-0 > .py-4")))
        print("Comments section found.")

        # --- Click "Load More Comments" until it's gone ---
        while True:
            try:
                load_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Load More Comments')]")
                print("Found 'Load More Comments' button. Clicking...")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                load_more_button.click()
                time.sleep(2) 
            except (NoSuchElementException, ElementClickInterceptedException):
                print("All comments loaded.")
                break

        # --- Find all comment blocks ---
        comments = driver.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4")
        
        if not comments:
            print("No comments were found on the page.")
            return None, 0

        print(f"Found {len(comments)} comments. Analyzing...")

        # --- Loop through each comment ---
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

    except TimeoutException:
        print("Timed out waiting for the comments section.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        driver.quit()

    return top_comment_text, highest_likes

# --- Main execution ---
if __name__ == "__main__":
    chapter_url = "https://asuracomic.net/series/omniscient-readers-viewpoint-a2adeda2/chapter/283"
    
    comment, likes = get_top_comment_from_page(chapter_url)

    if comment:
        print("\n--- Top Comment (Selenium-Only Method) ---")
        print(f"Likes: {likes}")
        print(f"Comment: \"{comment}\"")
    else:
        print("\nCould not retrieve the top comment.")