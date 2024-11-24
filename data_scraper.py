import re
import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import sys
from urllib.parse import urljoin
import os  # To ensure the folder exists

RATE = 0.0087
SET_LISTS_FILENAME="set_lists.json"

# Function to extract Civilization from the reference page
def get_civilization_and_japanese_name(reference_url):
    try:
        # Send a GET request to the reference URL
        response = requests.get(reference_url)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for tables with class 'wikitable'
            tables = soup.find_all('table', {'class': 'wikitable'})
            for table in tables:
                # Look at the first <tr> to find the Japanese Name in <small>
                first_row = table.find('tr')
                civilization = None
                japanese_name = None

                if first_row:
                    # Check for the <small> tag inside the first <tr>
                    small_tag = first_row.find('small')
                    if small_tag:
                        # Initialize a list to hold the ordered text parts
                        ordered_text = []

                        # Step 1: Split the <small> contents into text and <ruby> parts
                        contents = small_tag.contents

                        for content in contents:
                            if isinstance(content, str):  # This is text
                                ordered_text.append(content.strip())
                            elif content.name == 'ruby':  # This is a <ruby> tag
                                # Extract the text from <rb> inside the <ruby> tag
                                rb_tags = content.find_all('rb')
                                for rb in rb_tags:
                                    ordered_text.append(rb.get_text(strip=True))

                        # Join all parts into the final Japanese name
                        japanese_name = ''.join(ordered_text).strip()

                # Extract Civilization from the other rows
                rows = table.find_all('tr')
                for row in rows:
                    td = row.find_all('td')
                    if len(td) > 1:
                        # Extract Civilization text
                        if 'Civilization' in td[0].get_text(strip=True):
                            civilization = td[1].get_text(strip=True)

                if "colorless" in civilization.lower() or "colourless" in civilization.lower():
                    civilization = "Colourless"

                # If no civilization is found, return a default message
                if not civilization:
                    civilization = "Civilization Not Found"
                if not japanese_name:
                    japanese_name = "Japanese Name Not Found"
                
                return civilization, japanese_name
            return "Civilization Not Found", "Japanese Name Not Found"
        else:
            return "Failed to retrieve", "Failed to retrieve"
    except Exception as e:
        print(f"Error fetching Civilization and Japanese Name: {e}")
        return "Error", "Error"
    
def is_japanese_char(char):
    """Check if a character is Japanese."""
    codepoint = ord(char)
    return (
        (0x3040 <= codepoint <= 0x309F) or  # Hiragana
        (0x30A0 <= codepoint <= 0x30FF) or  # Katakana
        (0x31F0 <= codepoint <= 0x31FF) or  # Katakana Phonetic Extensions
        (0x4E00 <= codepoint <= 0x9FFF)     # Kanji
    )

def find_consecutive_japanese(text):
    # Ensure text has at least 3 characters
    if len(text) < 3:
        print(f"Failed to sanitize name for price search, falling back to {text}")
        return text

    # Check for three consecutive Japanese characters
    for i in range(len(text) - 1):  # Ensure there are at least 3 characters to compare
        if (
            is_japanese_char(text[i]) and
            is_japanese_char(text[i + 1])
        ):
            return text[i:i + 2]  # Return the three consecutive Japanese characters as a substring

    # If no consecutive Japanese characters, check for three consecutive alphabetic characters (both lowercase and uppercase)
    for i in range(len(text) - 2):
        if (
            text[i].isalpha() and text[i + 1].isalpha() and text[i + 2].isalpha()
        ):
            return text[i:i + 3]  # Return the three consecutive alphabetic characters as a substring

    # Return the original text if no match is found
    print(f"Failed to sanitize name for price search, falling back to {text}")
    return text

# Function to extract price from yuyutei
def fetch_highest_price(jap_name: str, card_id: str) -> int:
    base_url = "https://yuyu-tei.jp/sell/dm/s/search?search_word="
    complete_url = f"{base_url}{find_consecutive_japanese(jap_name)}%20{card_id}"

    # Fetch the webpage
    response = requests.get(complete_url)
    
    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(f"Failed to fetch URL: {complete_url}, status code: {response.status_code}")
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all <div> elements with id="class-list3"
    class_list3_divs = soup.find_all('div', id="card-list3")
    
    # Initialize a list to store prices
    prices = []
    
    for div in class_list3_divs:
        # Find all <div> elements with class="col-md" within the current <div>
        col_md_divs = div.find_all('div', class_="col-md")
        
        for col_md in col_md_divs:
            # Look for <span> with the specified class
            card_id_span = col_md.find('span', class_="d-block border border-dark p-1 w-100 text-center my-2")
            if card_id_span:
                # Sanitize page data
                card_id_parts = card_id_span.get_text(strip=True).split("｜")
                for no, id in enumerate(card_id_parts):
                    card_id_parts[no]=id.replace("ｂ", "b")
                    card_id_parts[no]=id.replace("Ultra ","超")

                if card_id in card_id_parts:
                    # Look for <strong> with the specified class
                    price_strong = col_md.find('strong', class_="d-block text-end") or col_md.find('strong', class_="d-block text-end text-danger")
                    if price_strong:
                        # Extract, clean, and convert the price text to an integer
                        price_text = price_strong.get_text(strip=True).replace(",", "").replace("円", "")
                        try:
                            prices.append(int(price_text))
                        except ValueError:
                            # Skip invalid prices
                            continue
    
    # Return the highest price in the list, or 0 if no prices found
    return max(prices, default=-1)

# Read the URL from the JSON file based on the parameter or return all URLs if no key is provided
def get_url_from_json(key=None):
    try:
        with open(SET_LISTS_FILENAME, "r") as json_file:
            url_data = json.load(json_file)
            if key:
                return url_data.get(key, None)
            else:
                return url_data  # Return all URLs if no key is provided
    except FileNotFoundError:
        print("URL data file not found.")
        return None

# Main function to run the scraping code
def scrape_website(url, key):
    start_time = time.time()

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        h2_tags = soup.find_all('h2')

        for h2 in h2_tags:
            span = h2.find('span')
            if span and "Contents" in span.get_text(strip=True):
                contents = []
                next_sibling = h2.find_next_sibling()

                cat = 'Over Rare'
                while next_sibling and next_sibling.name != 'h2':
                    if next_sibling.name == 'p':
                        cat = next_sibling.get_text(strip=True)
                        next_sibling = next_sibling.find_next_sibling()
                        continue
                    if next_sibling.name == 'ul':
                        for li in next_sibling.find_all('li'):
                            parts = li.decode_contents().split('<br/>')
                            for part in parts:
                                part_soup = BeautifulSoup(part, 'html.parser')
                                a_tag = part_soup.find('a')
                                if a_tag:
                                    english_name = str(a_tag.get_text(strip=True))
                                    item_link = urljoin(url, a_tag['href'])
                                    a_tag.extract()
                                else:
                                    english_name = "No link text"
                                    item_link = "No reference"

                                rarity = str(part_soup.get_text(strip=True))
                                split_rarity = [x.strip() for x in rarity.split(",")]
                                split_paragraph = [y.strip() for y in cat.split("/")]

                                # Check if any of the paragraph parts contains " Treasure"
                                treasure_part = [part for part in split_paragraph if " Treasure" in part]

                                # If " Treasure" exists in any part, add " Treasure" to those that do not have
                                if len(treasure_part) >= 1:
                                    for i in range(len(split_paragraph)):
                                        if " Treasure" not in split_paragraph[i]:
                                            split_paragraph[i] = split_paragraph[i] + " Treasure"

                                max_length = max(len(split_paragraph), len(split_rarity))
                                civilization, japanese_name = get_civilization_and_japanese_name(item_link)

                                for i in range(max_length):
                                    rarity = split_paragraph[i % len(split_paragraph)]

                                    # Sanitize card id
                                    card_id = split_rarity[i % len(split_rarity)]
                                    card_id = card_id.replace("☆", "")
                                    card_id = card_id.replace("㊙", "(秘)")
                                    card_id = card_id.replace("0R", "OR")
                                    card_id = re.sub(r'[\uFE00-\uFE0F]', '', card_id)
                                    if card_id.startswith("超G"):
                                        i=2
                                        check_done=False
                                        while i < len(card_id) and not check_done:
                                            if card_id[i] == "超":
                                                # If '超' is followed by 'G', add both to the result
                                                if i + 1 < len(card_id) and card_id[i + 1] == "G":
                                                    check_done=True
                                                else:
                                                    card_id=card_id[:i+1]+"G"+card_id[i+1:]
                                                    check_done=True
                                            else:
                                                i += 1  # Move to the next character


                                    price = fetch_highest_price(japanese_name, card_id)
                                    contents.append((english_name, japanese_name, rarity, card_id, item_link, civilization, price))

                    next_sibling = next_sibling.find_next_sibling()

                if contents:
                    # Ensure the directory exists
                    os.makedirs('./generated_csv', exist_ok=True)

                    # Dynamically generate the CSV filename using the key (the URL key)
                    csv_filename = f"./generated_csv/{key}.csv"
                    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        # Add "Set" column header
                        writer.writerow(["No", "Rarity", "Id", "Japanese Name", "English Name", "Civilization", "Set", "Reference", "Price (Yen)", "Price (SGD)", "Qty"])
                        for no, (english_name, japanese_name, rarity, id, reference, civilization, jp_price) in enumerate(contents, start=1):
                            # Write the data along with the key as the "Set" column
                            writer.writerow([no, rarity, id, japanese_name, english_name, civilization, key, reference, jp_price, round(jp_price*RATE, 2) if jp_price>-1 else jp_price, 0])

                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"Contents saved to {csv_filename}")
                    print(f"Scraping completed in {duration:.2f} seconds.")
                else:
                    print("No items found in the Contents section.")
                break
        else:
            print("Contents section not found.")
    else:
        print(f"Failed to fetch the webpage. Status code: {response.status_code}")


if __name__ == "__main__":
    url_data = get_url_from_json()

    # Check if a key was provided as a command-line argument
    if len(sys.argv) == 2:
        prompt = sys.argv[1].upper()
        found_key = False

        for key, url in url_data.items():
            if key.startswith(prompt.upper()):
                found_key = True
                print(f"Scraping data for {key}...")
                scrape_website(url, key)
                print(f"Resting...\n")
                time.sleep(5)

        if not found_key:
            print(f"No URLs found in {SET_LISTS_FILENAME}.")
        
    else:
        # If no key is provided, iterate over all key-value pairs in the JSON file
        if url_data:
            for key, url in url_data.items():
                print(f"Scraping data for {key}...")
                scrape_website(url, key)
                print(f"Resting...\n")
                time.sleep(5)
        else:
            print(f"No URLs found in {SET_LISTS_FILENAME}.")