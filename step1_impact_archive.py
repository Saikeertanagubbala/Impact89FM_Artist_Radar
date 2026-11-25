"""
Step 1: Pull Impact 89FM's interview + in-studio archive into a CSV.

Uses WordPress's built-in posts API (impact89fm.org/wp-json/...), which is
cleaner and gentler on the site than scraping HTML pages.
Get a quick okay from station leadership before running.

Output: impact_artists.csv
  post_id, date, year, category, title, artist_guess, url, word_count, has_text

After running, open the CSV and clean the artist_guess column by hand.
Titles are free text, so the guess will be wrong for some rows.

Run:  python step1_impact_archive.py
"""

import csv
import re
import time
import requests

BASE = "https://impact89fm.org/wp-json/wp/v2"

# Category slugs taken from the site's menu
CATEGORY_SLUGS = [
    "interview",              # Music > Interview
    "in-studio-performances", # Visual Media > In-Studio Performances
    "interviews-in-studios",  # Podcasts > Interviews & In-Studios
]

# A post with fewer words than this is probably just a video embed
TRANSCRIPT_MIN_WORDS = 300

HEADERS = {"User-Agent": "Impact89FM-archive-project (student research)"}


def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    return text


def guess_artist(title):
    # Common title patterns: "Artist | Something", "Artist - Something",
    # "Artist: Something", "In-Studio: Artist". Keep the most likely piece.
    title = strip_html(title).strip()
    for prefix in ["In-Studio:", "In Studio:", "Interview:", "The Basement"]:
        if title.lower().startswith(prefix.lower()):
            title = title[len(prefix):].strip(" -–|:")
    for sep in [" | ", " – ", " - ", ": "]:
        if sep in title:
            parts = []
            for piece in title.split(sep):
                piece = piece.strip()
                # Skip date pieces like "10/19/2023" (The Basement titles)
                if piece != "" and not re.fullmatch(r"[\d/.\-]+", piece):
                    parts.append(piece)
            if len(parts) == 0:
                return title
            # "Show - date - Artist" puts the artist last; otherwise first
            if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", title):
                return parts[-1]
            return parts[0]
    return title


def get_category_id(slug):
    r = requests.get(BASE + "/categories", params={"slug": slug}, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print("  Could not look up category", slug, "status", r.status_code)
        return None
    data = r.json()
    if len(data) == 0:
        print("  No category found for slug", slug)
        return None
    return data[0]["id"]


def main():
    rows = []
    seen_ids = set()

    for slug in CATEGORY_SLUGS:
        cat_id = get_category_id(slug)
        if cat_id is None:
            continue
        print("Category", slug, "-> id", cat_id)

        page = 1
        while True:
            params = {
                "categories": cat_id,
                "per_page": 50,
                "page": page,
                "_fields": "id,date,link,title,content",
            }
            r = requests.get(BASE + "/posts", params=params, headers=HEADERS, timeout=60)
            if r.status_code != 200:
                # WordPress returns 400 when you ask for a page past the end
                break
            posts = r.json()
            if len(posts) == 0:
                break

            for post in posts:
                if post["id"] in seen_ids:
                    continue
                seen_ids.add(post["id"])

                title = strip_html(post["title"]["rendered"]).strip()
                body = strip_html(post["content"]["rendered"])
                words = len(body.split())

                rows.append({
                    "post_id": post["id"],
                    "date": post["date"][:10],
                    "year": post["date"][:4],
                    "category": slug,
                    "title": title,
                    "artist_guess": guess_artist(title),
                    "url": post["link"],
                    "word_count": words,
                    "has_text": "yes" if words >= TRANSCRIPT_MIN_WORDS else "no",
                })

            print("  page", page, "->", len(posts), "posts")
            page += 1
            time.sleep(1)  # be polite to the station's server

    if len(rows) == 0:
        print("\nNo posts pulled. The WordPress API may be turned off.")
        print("Try opening https://impact89fm.org/wp-json/wp/v2/categories in a browser.")
        return

    rows.sort(key=lambda row: row["date"])

    with open("impact_artists.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # Quick summary
    per_year = {}
    with_text = 0
    for row in rows:
        per_year[row["year"]] = per_year.get(row["year"], 0) + 1
        if row["has_text"] == "yes":
            with_text += 1

    print("\nSaved", len(rows), "posts to impact_artists.csv")
    print("Posts with transcript-length text:", with_text)
    print("Posts per year:")
    for year in sorted(per_year):
        print(" ", year, per_year[year])


if __name__ == "__main__":
    main()
