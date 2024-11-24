import requests
from bs4 import BeautifulSoup

RATE=0.0087

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

def fetch_highest_price(jap_name: str, card_id: str) -> int:
    base_url = "https://yuyu-tei.jp/sell/dm/s/search?search_word="
    complete_url = f"{base_url}{find_consecutive_japanese(jap_name)}%20{card_id}"

    print(complete_url)
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

print(fetch_highest_price("der`ZenMondo", "5B/22"))