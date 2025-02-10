import re, json
import requests
from bs4 import BeautifulSoup


def crawl_x_tele_from_dexscreener(dex_url) -> dict:
    try:
        # Variables
        result = {}

        # Fetch the page content
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the script tag that contains JSON data
        script_tag = soup.find('script', type='application/json')

        # Check if script tag is found
        if script_tag:
            # Extract the JSON data from the script tag
            json_data = script_tag.string
            # Parse JSON data
            data = json.loads(json_data)
            
            # Extract token info
            token_info = data.get('props', {}).get('pageProps', {}).get('tokenInfo', {})
            result['liquidity_pool_value'] = round(token_info['liquidity'], 2)
            result['market_cap'] = round(token_info['market_cap'], 2)
            result['total_holder'] = token_info['holder_count']

            # Extract the social_links object
            social_links = data.get('props', {}).get('pageProps', {}).get('tokenInfo', {}).get('social_links', {})
            result['twitter_url'] = f"https://x.com/{social_links['twitter_username']}"
            result['website_url'] = social_links["website"]
            result['telegram_url']= social_links["telegram"]

            return result

        else:
            print("Script tag containing JSON data not found.")
            return None

    except (Exception) as e:
        print(f"Crawl x and tele func returned an error message: {e}")
        return None
    

def crawl_keyword(url, keyword):
    # Fetch the content of the URL
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch the URL: {url}")
        return

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Search for the keyword in the text
    body_text = soup.get_text().lower()

    match = re.search(r'(\d[\d\s]*)\s+subscribers', body_text)

    if match:
        subscribers = int(match.group(1).replace(" ",""))
        if subscribers:
            print(f"Subscribers: {subscribers}")


url = "https://gmgn.ai/sol/token/A8C3xuqscfmyLrte3VmTqrAq8kgMASius9AFNANwpump"
# url = "https://www.dextools.io/app/en/solana/pair-explorer/CQbXk942c6GPcRwtZ2WMFP5JcQ9NqbXtb8jUewBi7GoT"
print(crawl_x_tele_from_dexscreener(url))

# url = "https://t.me/fwogportal"
# keyword = "subscribers"
# crawl_keyword(url, keyword)
