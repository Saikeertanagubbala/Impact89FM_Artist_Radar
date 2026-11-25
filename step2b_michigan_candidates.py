"""
Step 2b: Find likely Michigan-based artists in the step 2 CSV.
No API calls - it only reads mi_setlists_<year>.csv.

An artist who played Michigan 3+ times in one year is a candidate for
"Michigan-based". Touring acts usually play the state once or twice.
(Step 2c, later, will confirm with each candidate's full show history.)

Output: mi_candidates_<year>.csv
  artist, artist_mbid, mi_shows, distinct_cities, distinct_venues, cities

Run:  python step2b_michigan_candidates.py 2019
"""

import csv
import sys

MIN_MI_SHOWS = 3


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "2019"
    filename = "mi_setlists_" + year + ".csv"

    # Group shows by artist
    artists = {}
    lansing_shows = 0
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["artist"]
            if name not in artists:
                artists[name] = {"mbid": row["artist_mbid"], "shows": 0, "cities": {}, "venues": {}}
            a = artists[name]
            a["shows"] += 1
            a["cities"][row["city"]] = a["cities"].get(row["city"], 0) + 1
            a["venues"][row["venue"]] = a["venues"].get(row["venue"], 0) + 1
            if row["city"] in ["Lansing", "East Lansing"]:
                lansing_shows += 1

    # Count how many artists fall in each show-count bucket
    buckets = {"1": 0, "2": 0, "3-4": 0, "5-9": 0, "10+": 0}
    for name in artists:
        n = artists[name]["shows"]
        if n == 1:
            buckets["1"] += 1
        elif n == 2:
            buckets["2"] += 1
        elif n <= 4:
            buckets["3-4"] += 1
        elif n <= 9:
            buckets["5-9"] += 1
        else:
            buckets["10+"] += 1

    # Keep the candidates
    rows = []
    for name in artists:
        a = artists[name]
        if a["shows"] >= MIN_MI_SHOWS:
            city_list = sorted(a["cities"].items(), key=lambda item: item[1], reverse=True)
            city_text = "; ".join(c + " (" + str(n) + ")" for c, n in city_list)
            rows.append({
                "artist": name,
                "artist_mbid": a["mbid"],
                "mi_shows": a["shows"],
                "distinct_cities": len(a["cities"]),
                "distinct_venues": len(a["venues"]),
                "cities": city_text,
            })
    rows.sort(key=lambda row: row["mi_shows"], reverse=True)

    out = "mi_candidates_" + year + ".csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artist", "artist_mbid", "mi_shows",
                                               "distinct_cities", "distinct_venues", "cities"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print("Michigan shows per artist in", year)
    for label in ["1", "2", "3-4", "5-9", "10+"]:
        print(" ", label, "shows:", buckets[label], "artists")
    print("\nShows in Lansing/East Lansing:", lansing_shows)
    print("Candidates with", MIN_MI_SHOWS, "+ Michigan shows:", len(rows), "-> saved to", out)
    print("\nTop 25 candidates (check by eye: local band or touring act?):")
    for row in rows[:25]:
        print(" ", row["mi_shows"], "|", row["artist"], "|", row["cities"])


if __name__ == "__main__":
    main()
