import requests
import json
import argparse
from bs4 import BeautifulSoup
import time  # Import the time module

# Start timing
start_time = time.time()

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Scrape links from a specific era in set_eras.json.")
parser.add_argument("key", type=str, help="The key to look up the URL in set_eras.json.")
args = parser.parse_args()

# Load the base URL from the JSON file
json_file = "set_eras.json"
try:
    with open(json_file, "r") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: The file {json_file} was not found.")
    exit()
except json.JSONDecodeError:
    print(f"Error: The file {json_file} is not a valid JSON file.")
    exit()

# Convert the input key to lowercase for case-insensitive comparison
input_key = args.key.lower()

# Get the URL for the specified key (case-insensitive)
base_url = None
for key, url in data.items():
    if key.lower() == input_key:
        base_url = url
        break

if not base_url:
    print(f"Error: No URL found for key '{args.key}' in {json_file}.")
    exit()

# The root base URL that will be prepended
root_url = "https://duelmasters.fandom.com"

# Target URL
target_url = base_url

# Make a GET request to fetch the page content
response = requests.get(target_url)
if response.status_code != 200:
    print(f"Failed to fetch the page. Status code: {response.status_code}")
    exit()

# Parse the page content with BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# Find all <h2> tags
h2_tags = soup.find_all("h2")

# Look for the <h2> with any <span> containing "Products"
products_header = None
for h2 in h2_tags:
    spans = h2.find_all("span")  # Find all <span> elements inside the <h2>
    for span in spans:
        if "Products" in span.get_text(strip=True):
            products_header = h2
            break
    if products_header:
        break

if not products_header:
    print("No <h2> tag with any <span> containing the text 'Products' found.")
    exit()

# Find all <ul> tags immediately following the <h2> tag
next_ul_tags = []
current_tag = products_header.find_next()
while current_tag:
    if current_tag.name == "ul":
        next_ul_tags.append(current_tag)
    elif current_tag.name == "h2":  # Stop if we reach the next <h2>
        break
    current_tag = current_tag.find_next()

# Initialize a list to collect all links
full_links = []

# For each <ul> found, look for <li> and then <a> tags within them
for ul_tag in next_ul_tags:
    li_tags = ul_tag.find_all("li")
    for li in li_tags:
        a_tag = li.find("a", href=True)  # Look for <a> tags inside <li>
        if a_tag:
            link = a_tag["href"]
            # Ensure no period is appended by ensuring the link is clean
            if not link.endswith("."):
                full_link = root_url + link  # Prepend root_url instead of base_url
                full_links.append(full_link)

# Now process each full_link
for link in full_links:
    # Make a GET request to fetch the page content for the current link
    response = requests.get(link)
    if response.status_code != 200:
        print(f"Failed to fetch the page: {link}. Status code: {response.status_code}")
        continue

    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <h2> tags on the page
    h2_tags = soup.find_all("h2")

    # Look for the <h2> with any <span> containing "List of Sets"
    list_of_sets_header = None
    for h2 in h2_tags:
        spans = h2.find_all("span")  # Find all <span> elements inside the <h2>
        for span in spans:
            if "List of Sets" in span.get_text(strip=True):
                list_of_sets_header = h2
                break
        if list_of_sets_header:
            break

    if not list_of_sets_header:
        print(f"No <h2> tag with any <span> containing the text 'List of Sets' found on {link}.")
        continue

    # Find all <ul> tags immediately following the <h2> tag
    next_ul_tags = []
    current_tag = list_of_sets_header.find_next()
    while current_tag:
        if current_tag.name == "ul":
            next_ul_tags.append(current_tag)
        elif current_tag.name == "h2":  # Stop if we reach the next <h2>
            break
        current_tag = current_tag.find_next()

    # Initialize a dictionary to collect all links for the current page
    page_links = {}

    # For each <ul> found, look for <li> and then <a> tags within them
    for ul_tag in next_ul_tags:
        li_tags = ul_tag.find_all("li")
        for li in li_tags:
            a_tag = li.find("a", href=True)  # Look for <a> tags inside <li>
            if a_tag:
                page_link = a_tag["href"]
                # Prepend root_url
                full_link = page_link if page_link.startswith('http') else root_url + page_link
                link_text = a_tag.get_text(strip=True).split(" ", 1)[0]  # Split and take the first part as the key
                page_links[link_text] = full_link

    # Now, load the existing data from set_lists.json
    set_lists_file = "set_lists.json"
    try:
        with open(set_lists_file, "r") as f:
            set_lists = json.load(f)
    except FileNotFoundError:
        set_lists = {}
    except json.JSONDecodeError:
        print(f"Error: The file {set_lists_file} is not a valid JSON file.")
        exit()

    # Update the set_lists with the new page_links
    set_lists.update(page_links)

    # Write the updated dictionary to set_lists.json
    with open(set_lists_file, "w") as f:
        json.dump(set_lists, f, indent=4)

    print(f"Links from {link} have been successfully added/updated in {set_lists_file}.")

# Calculate and print the time taken
end_time = time.time()
print(f"Time taken: {end_time - start_time:.2f} seconds")
