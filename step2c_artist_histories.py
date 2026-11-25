"""
Step 2c: Pull each candidate's full show history and decide who is
really Michigan-based.

Reads mi_candidates_<year>.csv (from step 2b) and, for each artist,
pages through all their setlists on setlist.fm. For every show it keeps
the date, city, state, country, and how many songs were covers.

Outputs:
  artist_shows.csv     - every show for every candidate (your raw training data)
  artist_summary.csv   - one row per artist with:
      total_shows, mi_shows, mi_share, first_year, last_year,
      songs_listed, cover_share, michigan_based, cover_band

Rules (change the numbers below if your mentor suggests different ones):
  michigan_based = at least 50% of all their shows were in Michigan
  cover_band     = at least 60% of listed songs were covers
                   (only judged if 20+ songs are listed)

The script can be stopped and restarted: it skips artists already in
artist_summary.csv. That matters because setlist.fm limits how many
requests you can make per day.

Needs SETLISTFM_API_KEY (same as step 2).
Run:  python step2c_artist_histories.py 2019
"""

import csv
import os
import sys
import time
import requests

API = "https://api.setlist.fm/rest/1.0"
SECONDS_BETWEEN = 0.6
MAX_PAGES_PER_ARTIST = 15   # 300 shows; big national acts get cut off here,
                            # which is fine because they get filtered out anyway
MI_SHARE_CUTOFF = 0.5
COVER_SHARE_CUTOFF = 0.6
MIN_SONGS_FOR_COVER_CHECK = 20

SHOW_FIELDS = ["artist", "artist_mbid", "date", "venue", "city", "state_code",
               "country_code", "in_michigan", "songs", "cover_songs"]
SUMMARY_FIELDS = ["artist", "artist_mbid", "total_shows", "mi_shows", "mi_share",
                  "first_year", "last_year", "songs_listed", "cover_share",
                  "pages_capped", "michigan_based", "cover_band"]


def count_songs(setlist):
    songs = 0
    covers = 0
    sets = setlist.get("sets", {}).get("set", [])
    for one_set in sets:
        for song in one_set.get("song", []):
            if song.get("tape"):
                continue  # songs played over the speakers, not performed
            songs += 1
            if "cover" in song:
                covers += 1
    return songs, covers


def fetch_history(mbid, headers):
    shows = []
    page = 1
    capped = False
    while True:
        if page > MAX_PAGES_PER_ARTIST:
            capped = True
            break
        r = requests.get(API + "/artist/" + mbid + "/setlists",
                         params={"p": page}, headers=headers, timeout=30)
        time.sleep(SECONDS_BETWEEN)

        if r.status_code == 404:
            break
        if r.status_code == 429:
            print("    rate limited, waiting 30 seconds...")
            time.sleep(30)
            continue
        if r.status_code != 200:
            print("    stopped, status", r.status_code)
            return None, capped  # None means "try this artist again next run"

        setlists = r.json().get("setlist", [])
        if len(setlists) == 0:
            break
        for s in setlists:
            shows.append(s)
        page += 1
    return shows, capped


def already_done():
    done = set()
    if os.path.exists("artist_summary.csv"):
        with open("artist_summary.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add(row["artist_mbid"])
    return done


def append_rows(filename, fields, rows):
    new_file = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    key = os.environ.get("SETLISTFM_API_KEY")
    if not key:
        print("Set SETLISTFM_API_KEY first.")
        return
    headers = {"x-api-key": key, "Accept": "application/json"}

    year = sys.argv[1] if len(sys.argv) > 1 else "2019"
    candidates = []
    with open("mi_candidates_" + year + ".csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["artist_mbid"] != "":
                candidates.append(row)

    done = already_done()
    todo = []
    for c in candidates:
        if c["artist_mbid"] not in done:
            todo.append(c)
    print(len(candidates), "candidates,", len(done), "already done,", len(todo), "to go")

    for i, c in enumerate(todo):
        name = c["artist"]
        mbid = c["artist_mbid"]
        print("[" + str(i + 1) + "/" + str(len(todo)) + "]", name)

        setlists, capped = fetch_history(mbid, headers)
        if setlists is None:
            print("Stopping early. Run the script again later to continue.")
            break

        show_rows = []
        mi_shows = 0
        total_songs = 0
        total_covers = 0
        years = []
        for s in setlists:
            venue = s.get("venue", {})
            city = venue.get("city", {})
            state = city.get("stateCode", "")
            country = city.get("country", {}).get("code", "")
            in_mi = (state == "MI" and country == "US")
            songs, covers = count_songs(s)

            if in_mi:
                mi_shows += 1
            total_songs += songs
            total_covers += covers
            date = s.get("eventDate", "")  # dd-MM-yyyy
            if len(date) == 10:
                years.append(int(date[6:]))

            show_rows.append({
                "artist": name, "artist_mbid": mbid, "date": date,
                "venue": venue.get("name", ""), "city": city.get("name", ""),
                "state_code": state, "country_code": country,
                "in_michigan": "yes" if in_mi else "no",
                "songs": songs, "cover_songs": covers,
            })

        total = len(show_rows)
        mi_share = mi_shows / total if total > 0 else 0
        cover_share = total_covers / total_songs if total_songs > 0 else 0

        michigan_based = mi_share >= MI_SHARE_CUTOFF and not capped
        cover_band = (total_songs >= MIN_SONGS_FOR_COVER_CHECK
                      and cover_share >= COVER_SHARE_CUTOFF)

        summary = {
            "artist": name, "artist_mbid": mbid,
            "total_shows": total, "mi_shows": mi_shows,
            "mi_share": round(mi_share, 2),
            "first_year": min(years) if years else "",
            "last_year": max(years) if years else "",
            "songs_listed": total_songs,
            "cover_share": round(cover_share, 2),
            "pages_capped": "yes" if capped else "no",
            "michigan_based": "yes" if michigan_based else "no",
            "cover_band": "yes" if cover_band else "no",
        }

        # Save after every artist so a stop or crash loses nothing
        append_rows("artist_shows.csv", SHOW_FIELDS, show_rows)
        append_rows("artist_summary.csv", SUMMARY_FIELDS, [summary])
        print("   ", total, "shows,", str(int(mi_share * 100)) + "% Michigan,",
              str(int(cover_share * 100)) + "% covers",
              "(capped)" if capped else "")

    # Final tally over everything collected so far
    keep = 0
    touring = 0
    covers = 0
    total = 0
    with open("artist_summary.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            if row["cover_band"] == "yes":
                covers += 1
            elif row["michigan_based"] == "no":
                touring += 1
            else:
                keep += 1
    print("\nArtists processed:", total)
    print("  Michigan-based originals (keep):", keep)
    print("  Mostly outside Michigan (drop):", touring)
    print("  Cover/tribute bands (drop):", covers)


if __name__ == "__main__":
    main()
