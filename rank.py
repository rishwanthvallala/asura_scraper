import json
from tabulate import tabulate

def rank_manhwa_by_likes(file_path='results.json'):
    """
    Reads the results.json file, calculates the max likes for each manhwa,
    and prints a ranked table of the top 50.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        print("Please make sure the scraped data is saved correctly.")
        return

    manhwa_scores = []
    for manhwa in data:
        title = manhwa.get("title")
        chapters = manhwa.get("processed_chapters", [])
        
        max_likes = 0
        if chapters:
            # Find the highest like count among the processed chapters for this manhwa
            like_counts = [chapter.get("likes", 0) for chapter in chapters]
            if like_counts:
                max_likes = max(like_counts)
        
        if title:
            manhwa_scores.append({
                "title": title,
                "max_likes": max_likes
            })

    # Sort the list of manhwa by their max_likes score in descending order
    sorted_manhwa = sorted(manhwa_scores, key=lambda item: item['max_likes'], reverse=True)

    # Prepare data for the table display
    top_50_manhwa = sorted_manhwa[:50]
    display_data = []
    for i, item in enumerate(top_50_manhwa, 1):
        display_data.append([
            i,
            item['title'],
            item['max_likes']
        ])

    # Print the formatted table
    headers = ["Rank", "Manhwa Title", "Highest Like Count in Recent Chapters"]
    print("\n--- Top 50 Manhwa by Peak Comment Likes ---")
    print(tabulate(display_data, headers=headers, tablefmt="heavy_grid"))

if __name__ == "__main__":
    rank_manhwa_by_likes()