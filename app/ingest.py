import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path
from tqdm import tqdm

# -------------------- CONFIG --------------------
BANG_URL = "https://en.banglapedia.org"
BANG_SEARCH = BANG_URL + "/index.php"
WIKI_URL = "https://en.wikipedia.org"
DIVISIONS = ["Dhaka", "Chittagong", "Khulna", "Sylhet", "Barisal", "Rajshahi", "Rangpur", "Mymensingh"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

# -------------------- ENHANCED DIVISION ASSIGNMENT --------------------
def assign_divisions(places):
    """
    Enhanced division assignment with better keyword matching
    """
    division_keywords = {
        "Dhaka": {
            "exact": ["dhaka"],
            "keywords": ["buriganga", "lalbagh", "ahsan manzil", "national museum", 
                        "shahbag", "ramna", "dhanmondi", "gulshan", "uttara",
                        "old dhaka", "sadarghat"],
        },
        "Chittagong": {
            "exact": ["chittagong", "chattogram"],
            "keywords": ["cox's bazar", "cox bazar", "coxs bazar", "patenga", 
                        "foy's lake", "kaptai", "rangamati", "khagrachari",
                        "bandarban", "sitakunda", "mirsharai"],
        },
        "Khulna": {
            "exact": ["khulna"],
            "keywords": ["sundarbans", "sundarban", "bagerhat", "mongla", 
                        "kuakata", "satkhira"],
        },
        "Sylhet": {
            "exact": ["sylhet"],
            "keywords": ["ratargul", "jaflong", "madhabkunda", "lalakhal", 
                        "srimangal", "sreemangal", "tea garden", "tamabil"],
        },
        "Barisal": {
            "exact": ["barisal", "barishal"],
            "keywords": ["kuakata", "durga sagar", "patuakhali", "bhola"],
        },
        "Rajshahi": {
            "exact": ["rajshahi"],
            "keywords": ["paharpur", "bagha", "puthia", "varendra", "natore"],
        },
        "Rangpur": {
            "exact": ["rangpur"],
            "keywords": ["tetulia", "nilphamari", "dinajpur", "kantaji"],
        },
        "Mymensingh": {
            "exact": ["mymensingh"],
            "keywords": ["shashi lake", "brahmaputra", "jamalpur"],
        }
    }

    for place in places:
        if not place.get("division") or place.get("division") == "Unknown":
            desc = (place.get("description") or "").lower()
            name = (place.get("name") or "").lower()
            url = (place.get("url") or "").lower()
            
            combined_text = f"{name} {desc} {url}"
            assigned = False
            
            # First try exact matches in name (highest priority)
            for div, patterns in division_keywords.items():
                for exact in patterns["exact"]:
                    if exact in name:
                        place["division"] = div
                        assigned = True
                        break
                if assigned:
                    break
            
            # Then try exact matches in URL
            if not assigned:
                for div, patterns in division_keywords.items():
                    for exact in patterns["exact"]:
                        if exact in url:
                            place["division"] = div
                            assigned = True
                            break
                    if assigned:
                        break
            
            # Then try keywords anywhere
            if not assigned:
                for div, patterns in division_keywords.items():
                    for kw in patterns["keywords"]:
                        if kw in combined_text:
                            place["division"] = div
                            assigned = True
                            break
                    if assigned:
                        break
            
            # Still not assigned? Keep as Unknown
            if not assigned:
                place["division"] = "Unknown"
    
    return places

# -------------------- CATEGORY ASSIGNMENT --------------------
def assign_categories(places):
    """
    Assign categories to places based on their content
    """
    category_keywords = {
        "Beach": ["beach", "sea", "ocean", "coast", "marine"],
        "Hill": ["hill", "mountain", "highland", "valley"],
        "Lake": ["lake", "water", "reservoir"],
        "Forest": ["forest", "jungle", "wildlife", "sanctuary", "mangrove"],
        "Historical": ["historical", "ancient", "heritage", "archaeological", "monument", "fort", "palace"],
        "Religious": ["mosque", "temple", "church", "monastery", "shrine", "religious"],
        "Park": ["park", "garden", "botanical"],
        "Waterfall": ["waterfall", "fall", "cascade"],
        "Island": ["island", "char"],
        "Tea Garden": ["tea", "garden", "estate"],
        "Museum": ["museum", "gallery"],
        "River": ["river", "ghat"]
    }
    
    for place in places:
        desc = (place.get("description") or "").lower()
        name = (place.get("name") or "").lower()
        combined = f"{name} {desc}"
        
        categories = []
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in combined:
                    categories.append(category)
                    break
        
        place["categories"] = categories if categories else ["General"]
    
    return places

# -------------------- SCRAPE FUNCTIONS (keeping your original ones) --------------------
def search_banglapedia(division):
    """Search Banglapedia for tourist spots in a given division."""
    query = f"tourist spot {division}"
    try:
        resp = requests.get(BANG_SEARCH, params={"search": query}, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Search failed for {division} (status {resp.status_code})")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select("ul.mw-search-results li")
        places = []
        for r in results:
            link = r.select_one("a")
            if not link:
                continue
            href = link.get("href")
            if href and not href.startswith("http"):
                href = BANG_URL + href
            name = link.text.strip()
            places.append({"name": name, "url": href, "division": division})
        return places
    except Exception as e:
        print(f"❌ Error searching Banglapedia for {division}: {e}")
        return []

def search_wikipedia():
    """Scrape Wikipedia category page for tourist attractions in Bangladesh."""
    url = WIKI_URL + "/wiki/Category:Tourist_attractions_in_Bangladesh"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print("⚠️ Wikipedia search failed")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("div.mw-category a")
        places = []
        for link in links:
            href = link.get("href")
            if href and href.startswith("/wiki/"):
                full_url = WIKI_URL + href
                name = link.text.strip()
                places.append({"name": name, "url": full_url, "division": None})
        return places
    except Exception as e:
        print(f"❌ Error searching Wikipedia: {e}")
        return []

def fetch_details(place, source="banglapedia"):
    """Fetch description and image from a page (Banglapedia or Wikipedia)."""
    try:
        resp = requests.get(place["url"], headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract first paragraphs as description
        paras = soup.select("div.mw-parser-output > p")
        desc_parts = []
        for p in paras[:3]:  # Get more paragraphs for better context
            text = p.get_text(strip=True)
            if len(text) > 20:  # Skip very short paragraphs
                desc_parts.append(text)
        
        desc = " ".join(desc_parts)
        desc = re.sub(r"\[.*?\]", "", desc)  # Remove references

        # Extract image
        img_tag = soup.select_one("div.mw-parser-output img, img.thumbimage")
        img_url = None
        if img_tag:
            src = img_tag.get("src")
            if src:
                if src.startswith("//"):
                    img_url = "https:" + src
                elif src.startswith("/"):
                    img_url = (BANG_URL if source == "banglapedia" else WIKI_URL) + src
                else:
                    img_url = src

        place["description"] = desc
        place["image"] = img_url
        return place
    except Exception as e:
        print(f"❌ Error fetching {place.get('name')}: {e}")
        return None

# -------------------- MAIN SCRAPER --------------------
def scrape_all():
    all_places = []

    # Banglapedia
    print("\n" + "="*50)
    print("🌍 SCRAPING BANGLAPEDIA")
    print("="*50)
    for div in DIVISIONS:
        print(f"\n📍 Searching {div}...")
        results = search_banglapedia(div)
        print(f"   ➜ Found {len(results)} results")
        
        for p in tqdm(results, desc=f"Fetching details for {div}"):
            d = fetch_details(p, source="banglapedia")
            if d and d.get("description"):  # Only add if has description
                all_places.append(d)
            time.sleep(0.5)  # Be nice to the server
        
        time.sleep(1)

    # Wikipedia
    print("\n" + "="*50)
    print("📘 SCRAPING WIKIPEDIA")
    print("="*50)
    wiki_places = search_wikipedia()
    print(f"   ➜ Found {len(wiki_places)} wiki-spots")
    
    for p in tqdm(wiki_places, desc="Fetching wiki details"):
        d = fetch_details(p, source="wiki")
        if d and d.get("description"):
            all_places.append(d)
        time.sleep(0.5)

    # Deduplicate by name (case-insensitive)
    print("\n🔄 Deduplicating...")
    seen = {}
    unique_places = []
    for p in all_places:
        name_key = p["name"].lower().strip()
        if name_key not in seen:
            seen[name_key] = True
            unique_places.append(p)
        else:
            # If duplicate, merge information (keep the one with more description)
            existing_idx = next(i for i, x in enumerate(unique_places) if x["name"].lower().strip() == name_key)
            if len(p.get("description", "")) > len(unique_places[existing_idx].get("description", "")):
                unique_places[existing_idx] = p

    print(f"   ➜ {len(all_places)} total → {len(unique_places)} unique")

    # Assign divisions and categories
    print("\n🏷️ Assigning divisions and categories...")
    unique_places = assign_divisions(unique_places)
    unique_places = assign_categories(unique_places)
    
    # Print statistics
    print("\n📊 STATISTICS:")
    division_counts = {}
    for p in unique_places:
        div = p.get("division", "Unknown")
        division_counts[div] = division_counts.get(div, 0) + 1
    
    for div, count in sorted(division_counts.items()):
        print(f"   {div}: {count} places")

    return unique_places

def save_to_json(data, path="../data/places.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {len(data)} places to {path}")

def ingest_data():
    """Main function to run data ingestion"""
    print("\n🚀 Starting BD Tour Guide Data Ingestion...")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    start_time = time.time()
    data = scrape_all()
    save_to_json(data)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Total time: {elapsed:.2f} seconds")
    print("🎉 Data ingestion complete!\n")

# -------------------- RUN --------------------
if __name__ == "__main__":
    ingest_data()