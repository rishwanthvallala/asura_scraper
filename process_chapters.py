# File: process_chapters.py
#
# Improved version:
# - Persistent browser sessions (one Chrome per worker, reused across URLs)
# - Resume support: skips already-scraped URLs (replaces fill_gaps.py)
# - Incremental saves after every completed URL (crash-safe)
# - Auto-retry up to MAX_RETRIES times on failure
# - StaleElementReference fix: re-fetch comment list by index instead of holding refs

import json
import time
import threading
import collections
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    ElementClickInterceptedException, StaleElementReferenceException
)

MAX_WORKERS = 8
MAX_RETRIES = 2
MAX_LOAD_MORE = 5   # Top comment by likes is almost always in first few batches
RESULTS_FILE = 'results.json'
CHAPTER_LIST_FILE = 'chapter_list.json'

# Lock for thread-safe writes to results.json
_save_lock = threading.Lock()

# --- Metrics ---
_metrics = {
    'completed': 0,
    'failed': 0,
    'total_url_time': 0.0,    # cumulative seconds spent scraping URLs
    'load_more_clicks': 0,
    'recent_times': collections.deque(maxlen=20),  # rolling window for throughput calc
}
_metrics_lock = threading.Lock()
_run_start = None  # wall-clock start, set in __main__


def _print_progress(total_pending, run_start):
    with _metrics_lock:
        done = _metrics['completed']
        failed = _metrics['failed']
        total_time = _metrics['total_url_time']

    elapsed_wall = time.perf_counter() - run_start
    avg_per_url = (total_time / done) if done else 0
    # Wall-clock throughput accounts for parallelism correctly
    wall_throughput = (done / elapsed_wall) if elapsed_wall > 0 else 0  # URLs/sec

    remaining = total_pending - done - failed
    eta_sec = (remaining / wall_throughput) if wall_throughput > 0 else 0
    eta_min = eta_sec / 60

    print(
        f"[{done+failed}/{total_pending}] done={done} failed={failed} | "
        f"avg {avg_per_url:.1f}s/url | "
        f"throughput {wall_throughput*60:.1f} urls/min | "
        f"ETA ~{eta_min:.0f}min | "
        f"elapsed {elapsed_wall/60:.1f}min"
    )


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--log-level=3')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    return webdriver.Chrome(service=webdriver.ChromeService(), options=options)


def scrape_url_with_driver(driver, url):
    """
    Scrape a single URL using an existing driver instance.
    Returns {"comment": str, "likes": int} or raises on failure.
    """
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".space-y-0 > .py-4")))

    # Click "Load More Comments" until gone or cap reached
    load_more_count = 0
    for _ in range(MAX_LOAD_MORE):
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Load More Comments')]")
            prev_count = len(driver.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4"))
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            load_more_count += 1
            # Wait until new comments appear (up to 3s), instead of a fixed sleep
            try:
                WebDriverWait(driver, 3).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4")) > prev_count
                )
            except TimeoutException:
                pass
        except (NoSuchElementException, ElementClickInterceptedException):
            break

    with _metrics_lock:
        _metrics['load_more_clicks'] += load_more_count

    # Re-fetch by index to avoid stale refs from clicking Load More
    highest_likes = -1
    top_comment_text = ""
    comment_count = len(driver.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4"))

    for i in range(comment_count):
        try:
            comments = driver.find_elements(By.CSS_SELECTOR, ".space-y-0 > .py-4")
            comment = comments[i]
            like_btn = comment.find_element(
                By.CSS_SELECTOR, "button[data-tooltip-content='Login to like this comment']"
            )
            current_likes = int(like_btn.find_element(By.TAG_NAME, "span").text)
            if current_likes > highest_likes:
                highest_likes = current_likes
                top_comment_text = comment.find_element(By.CSS_SELECTOR, ".prose p").text
        except (NoSuchElementException, StaleElementReferenceException, ValueError, IndexError):
            continue

    return {"comment": top_comment_text, "likes": highest_likes}


def worker(urls_queue, scraped_map, title_to_urls, total_pending, run_start):
    """
    Worker that holds one persistent browser and processes URLs from the queue.
    Saves results incrementally after each success.
    """
    driver = make_driver()
    try:
        while True:
            try:
                url = urls_queue.pop()
            except IndexError:
                break

            result = None
            t0 = time.perf_counter()
            for attempt in range(1, MAX_RETRIES + 2):  # +2 because range is exclusive
                try:
                    result = scrape_url_with_driver(driver, url)
                    break
                except Exception as e:
                    if attempt <= MAX_RETRIES:
                        print(f"Retry {attempt}/{MAX_RETRIES} for {url}: {type(e).__name__}")
                        time.sleep(2)
                    else:
                        print(f"Failed after {MAX_RETRIES} retries: {url}")

            elapsed = time.perf_counter() - t0

            if result:
                with _metrics_lock:
                    _metrics['completed'] += 1
                    _metrics['total_url_time'] += elapsed
                    _metrics['recent_times'].append(elapsed)
                with _save_lock:
                    scraped_map[url] = result
                    save_results(title_to_urls, scraped_map)
                _print_progress(total_pending, run_start)
            else:
                with _metrics_lock:
                    _metrics['failed'] += 1
                print(f"Skipping (all retries exhausted): {url}")
    finally:
        driver.quit()


def load_existing_results():
    """
    Load results.json if it exists.
    Returns:
      scraped_map: url -> {comment, likes}
      title_to_urls: title -> [ordered list of all known urls for that title]
    """
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        scraped_map = {}
        title_to_urls = {}
        for manhwa in data:
            title = manhwa['title']
            urls = []
            for chap in manhwa.get('processed_chapters', []):
                scraped_map[chap['url']] = {
                    'comment': chap['top_comment'],
                    'likes': chap['likes']
                }
                urls.append(chap['url'])
            title_to_urls[title] = urls
        return scraped_map, title_to_urls
    except FileNotFoundError:
        return {}, {}


def merge_new_urls(title_to_urls, manhwa_list):
    """
    Merge URLs from chapter_list.json into title_to_urls without removing any existing ones.
    New URLs are appended; titles not yet seen are added fresh.
    """
    for manhwa in manhwa_list:
        title = manhwa['title']
        existing = title_to_urls.get(title)
        if existing is None:
            title_to_urls[title] = list(manhwa['chapters'])
        else:
            existing_set = set(existing)
            for url in manhwa['chapters']:
                if url not in existing_set:
                    existing.append(url)
                    existing_set.add(url)


def save_results(title_to_urls, scraped_map):
    """Rebuild and overwrite results.json, preserving all ever-scraped chapters per title."""
    final_data = []
    for title, urls in title_to_urls.items():
        processed = []
        for url in urls:
            if url in scraped_map:
                r = scraped_map[url]
                processed.append({
                    'url': url,
                    'top_comment': r['comment'],
                    'likes': r['likes']
                })
        final_data.append({
            'title': title,
            'processed_chapters': processed
        })
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)


if __name__ == "__main__":
    try:
        with open(CHAPTER_LIST_FILE, 'r', encoding='utf-8') as f:
            manhwa_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: {CHAPTER_LIST_FILE} not found. Run collect_urls.py first.")
        exit()

    # Load any previously scraped results + all known URLs per title
    scraped_map, title_to_urls = load_existing_results()
    already_done = len(scraped_map)

    # Merge new URLs from chapter_list.json without dropping old ones
    merge_new_urls(title_to_urls, manhwa_list)

    # Build queue of all known URLs not yet scraped
    all_known_urls = [url for urls in title_to_urls.values() for url in urls]
    pending = [url for url in all_known_urls if url not in scraped_map]

    print(f"Total known chapters: {len(all_known_urls)} | Already scraped: {already_done} | Remaining: {len(pending)}")

    if not pending:
        print("✅ All chapters already scraped. Nothing to do.")
        exit()

    # Use a simple list as a thread-safe-ish queue (pop from end)
    urls_queue = list(reversed(pending))
    total_pending = len(pending)

    _run_start = time.perf_counter()

    threads = []
    for _ in range(min(MAX_WORKERS, total_pending)):
        t = threading.Thread(target=worker, args=(urls_queue, scraped_map, title_to_urls, total_pending, _run_start))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    wall_time = time.perf_counter() - _run_start
    newly_done = _metrics['completed']
    failed = _metrics['failed']
    avg = (_metrics['total_url_time'] / newly_done) if newly_done else 0
    throughput = (newly_done / wall_time * 60) if wall_time > 0 else 0

    print(f"\n{'='*60}")
    print(f"✅ Run complete in {wall_time/60:.1f} min ({wall_time:.0f}s)")
    print(f"   Scraped:   {newly_done} URLs")
    print(f"   Failed:    {failed} URLs")
    print(f"   Avg time:  {avg:.1f}s per URL")
    print(f"   Throughput: {throughput:.1f} URLs/min")
    print(f"   Load More clicks total: {_metrics['load_more_clicks']}")
    print(f"   Workers: {min(MAX_WORKERS, total_pending)}")
    print(f"{'='*60}")
    print(f"Results saved to {RESULTS_FILE}.")
