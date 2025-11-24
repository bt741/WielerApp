# python
import json
import requests
from bs4 import BeautifulSoup, FeatureNotFound

"""
    Only use this if you want to re-fetch the province mapping from Wikipedia.
    This will produce 'province_map.json' which is used by the main program.
    Note that a lot of typo's are on the wikipedia page, manual fixing may be required.
    Using this function is not part of the normal program flow, and heavily discouraged.
"""
def fetch_provinces():
    INPUT = [
        {
            "url": "https://nl.wikipedia.org/wiki/Lijst_van_gemeenten_in_het_Vlaams_Gewest",
            "keywords": {
                "name": "gemeente",
                "province": "provincie",
            }
        },
        {
            "url": "https://fr.wikipedia.org/wiki/Liste_des_communes_de_la_R%C3%A9gion_wallonne",
            "keywords": {
                "name": "nom français",
                "province": "province",
            }
        },
        {
            "url": "https://fr.wikipedia.org/wiki/Liste_des_communes_de_la_r%C3%A9gion_de_Bruxelles-Capitale",
            "keywords": {
                "name": "nom français",
                "province": "nom français",
            }
        }
    ]

    OUT_FILE = "province_map.json"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    def fetch(url):
        resp = requests.get(url, headers=headers, timeout=20)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            # If Wikipedia returns 403, retry with printable view
            if resp.status_code == 403:
                printable = url + "?printable=yes"
                resp = requests.get(printable, headers=headers, timeout=20)
                resp.raise_for_status()
            else:
                raise
        return resp

    items = {}

    for entry in INPUT:
        url = entry["url"]
        name_keyword = entry["keywords"]["name"]
        prov_keyword = entry["keywords"]["province"]

        resp = fetch(url)
        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except FeatureNotFound:
            soup = BeautifulSoup(resp.text, "html.parser")

        tables = soup.find_all("table", class_="wikitable")
        target_table = None
        for tbl in tables:
            # collect header cell texts robustly (joins nested text, strips whitespace, lowercases)
            headers_cells = [" ".join(th.stripped_strings).lower() for th in tbl.find_all("th")]

            # match any reasonable variants for the municipality/name and province columns
            name_matches = any(name_keyword in h for h in headers_cells)
            province_matches = any(prov_keyword in h for h in headers_cells)

            if name_matches and province_matches:
                target_table = tbl
                break
        if target_table is None:
            raise SystemExit("Could not find table with municipality and province headers on page: " + url)

        header_cells = [th.get_text(strip=True).lower() for th in target_table.find_all("th")]
        print(header_cells)
        def find_index(key_words):
            for i, txt in enumerate(header_cells):
                for kw in key_words:
                    if kw in txt:
                        return i
            return None

        name_idx = find_index(["commune", "name", "dutch name"])
        province_idx = find_index(["province", "provincie"])

        if name_idx is None:
            name_idx = 0
        if province_idx is None:
            province_idx = 1

        for row in target_table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_idx, province_idx):
                continue
            def cell_text(cell):
                return cell.get_text(" ", strip=True)
            name = cell_text(cells[name_idx]).upper().split(" ")[0]
            province = cell_text(cells[province_idx]).upper()
            if name and province:
                if prov_keyword == name_keyword:
                    items[name] = "BRUSSEL"
                else:
                    items[name] = province.split("PROVINCE DE ")[-1].split("PROVINCE DU ")[-1]

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(items)} entries to {OUT_FILE}")