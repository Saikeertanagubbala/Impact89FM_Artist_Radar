"""
Step 2: Count how many artists setlist.fm has for Michigan in one year.

This is the number that decides whether the training set is big enough.
Rough rule: a few hundred distinct artists in one year = go.

Needs a free setlist.fm API key (non-commercial use):
  https://www.setlist.fm/settings/api
Set it as an environment variable before running:
  Mac/Linux:  export SETLISTFM_API_KEY="your-key"
  Windows:    set SETLISTFM_API_KEY=PMBhA8ulZOXeE_ZFqEX3vsn-fXdZbOH77bc9

Output: mi_setlists_<year>.csv
  date, artist, artist_mbid, venue, city

Run:  python step2_setlist_michigan.py 2019
"""

import csv
import os
import sys
import time
import requests

API = "https://api.setlist.fm/rest/1.0"
MAX_PAGES = 400        # 20 setlists per page, so up to 8,000 shows
SECONDS_BETWEEN = 0.6  # stay under roughly 2 requests per second


def main():
    key = "PMBhA8ulZOXeE_ZFqEX3vsn-fXdZbOH77bc9" #os.environ.get("SETLISTFM_API_KEY")
    if not key:
        print("Set SETLISTFM_API_KEY first (see the top of this file).")
        return

    year = sys.argv[1] if len(sys.argv) > 1 else "2019"
    headers = {"x-api-key": key, "Accept": "application/json"}

    rows = []
    page = 1
    total = None

    while page <= MAX_PAGES:
        params = {"stateCode": "MI", "countryCode": "US", "year": year, "p": page}
        r = requests.get(API + "/search/setlists", params=params, headers=headers, timeout=30)

        if r.status_code == 404:
            break  # setlist.fm returns 404 when there are no more results
        if r.status_code == 429:
            print("Rate limited, waiting 10 seconds...")
            time.sleep(10)
            continue
        if r.status_code != 200:
            print("Stopped on page", page, "status", r.status_code, r.text[:200])
            break

        data = r.json()
        if total is None:
            total = data.get("total", 0)
            print("setlist.fm reports", total, "Michigan setlists in", year)

        setlists = data.get("setlist", [])
        if len(setlists) == 0:
            break

        for s in setlists:
            artist = s.get("artist", {})
            venue = s.get("venue", {})
            city = venue.get("city", {})
            rows.append({
                "date": s.get("eventDate", ""),
                "artist": artist.get("name", ""),
                "artist_mbid": artist.get("mbid", ""),
                "venue": venue.get("name", ""),
                "city": city.get("name", ""),
            })

        if page % 10 == 0:
            print("  page", page, "- rows so far:", len(rows))
        page += 1
        time.sleep(SECONDS_BETWEEN)

    if len(rows) == 0:
        print("No setlists returned.")
        return

    filename = "mi_setlists_" + year + ".csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # Count distinct artists and shows per artist
    shows_per_artist = {}
    cities = {}
    for row in rows:
        name = row["artist"]
        shows_per_artist[name] = shows_per_artist.get(name, 0) + 1
        cities[row["city"]] = cities.get(row["city"], 0) + 1

    one_show = 0
    for name in shows_per_artist:
        if shows_per_artist[name] == 1:
            one_show += 1

    print("\nSaved", len(rows), "setlists to", filename)
    print("Distinct artists:", len(shows_per_artist))
    print("Artists with only 1 Michigan show that year:", one_show)
    print("Top 10 cities:")
    top_cities = sorted(cities.items(), key=lambda item: item[1], reverse=True)[:10]
    for city, count in top_cities:
        print(" ", city, count)


if __name__ == "__main__":
    main()
