import requests
import re
import urllib.request
from bs4 import BeautifulSoup
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urlparse
import os
from upstream_object import InferenceUtils
from utils import generate_uuid
from db_utils import write_to_db
from constants import DTYPE_PNG

from logger_config import setup_logger
logger = setup_logger(__name__)

# Get from ENV the path to the driver
CHROME_DRIVER_PATH = os.environ.get("CHROME_DRIVER_PATH", None)

# Regex pattern to match a URL
HTTP_URL_PATTERN = r'^http[s]*://.+'

# Define root domain to crawl
domain = "pablofelgueres.com"
full_url = "https://pablofelgueres.com"

def preflight_url_validation_headless(url, user_id):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options 

    base_folder = os.path.dirname(os.path.abspath(__file__))
    users_folder = os.path.join(base_folder, 'users')
    user_folder = os.path.join(users_folder, user_id)

    if not os.path.exists(users_folder):
        os.makedirs(users_folder)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    try:
        service = Service(os.path.join(base_folder, CHROME_DRIVER_PATH))
        service.start()
        options = Options()
        user_agent = 'Mozilla/5.0' 
        accept_language = 'en-US,en;q=0.9'
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument(f'accept-language={accept_language}')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=service, options=options)
        logger.info('Driver init with success')
        
    except Exception as e:
        logger.info('driver error', e)
        return {"error": 'Error fetching source. Please try again.'}, False

    source_id = generate_uuid(8)
    sum_tokens = 0

    try:
        driver.get(url)
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, total_height)
        source_path = os.path.join(user_folder, source_id + '.png')
        driver.save_screenshot(source_path)

        with open(source_path, 'rb') as f:
            data = f.read()
            add_blob_q = '''INSERT INTO blobs (source_id,data,dtype) VALUES (?,?,?)'''
            blob_entry = (source_id, data, DTYPE_PNG)
            write_to_db(add_blob_q, blob_entry)
    
        text = driver.find_element(By.TAG_NAME, "body").text
        name = driver.title
    
    except Exception as e:
        return {"error": str(e)}, False 

    finally:
        driver.quit()
        os.remove(source_path) if os.path.exists(source_path) else None

    n_tokens = InferenceUtils.num_tokens_from_string(text)
    sum_tokens += n_tokens
    res = {"url": url, "n_tokens": n_tokens, "content": text, "link_id": generate_uuid(4), "source_id": source_id, 'name': name}
    return res, True

def preflight_urls_validation_headless(url, max_pages=15, max_tokens=10000):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options 

    base_folder = os.path.dirname(os.path.abspath(__file__))

    try:
        logger.info('Starting service')
        service = Service(os.path.join(base_folder, CHROME_DRIVER_PATH))
        service.start()
        options = Options()
        user_agent = 'Mozilla/5.0' 
        accept_language = 'en-US,en;q=0.9'
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument(f'accept-language={accept_language}')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=service, options=options)
        logger.info('Driver init with success')
        
    except Exception as e:
        logger.info('driver error', e)
        return {"error": str(e)}

    # get local domain from url
    local_domain = urlparse(url).netloc 

    links = [] 
    seen = set([url])
    queue = deque([url])
    source_id = generate_uuid(8)
    sum_tokens = 0
    processed = 0

    try:
        while queue:
            cur_url = queue.pop()
            driver.get(cur_url)
            text = driver.find_element(By.TAG_NAME, "body").text
            n_tokens = InferenceUtils.num_tokens_from_string(text)
            sum_tokens += n_tokens
            links.append({"url": cur_url, "n_tokens": n_tokens, "content": text, "link_id": generate_uuid(4)})
            processed += 1
            if processed > max_pages: break
            for link in get_domain_hyperlinks_headless(driver, local_domain, cur_url): 
                link = link.strip("/")
                if link not in seen: 
                    print('adding link', link)
                    if len(seen) > max_pages or sum_tokens > max_tokens :
                        break
                    queue.append(link)
                    seen.add(link)
    
        # close driver
        driver.quit()
        return { "source_id": source_id, "links": links }
    
    except Exception as e:
        print('Exception fetching links', e)
        driver.quit()
        return {"error": str(e)}

# Function to get the hyperlinks from a URL
def get_hyperlinks_headless(driver, url):
    # Try to open the URL and read the HTML
    try:
        driver.get(url)
        # If the response is not HTML, return an empty list
        if not driver.page_source:
            return []
        # Decode the HTML
        html = driver.page_source
    except Exception as e:
        print(e)
        return []
    # Create the HTML Parser and then Parse the HTML to get hyperlinks
    parser = HyperlinkParser()
    parser.feed(html)
    return parser.hyperlinks

# Function to get the hyperlinks from a URL that are within the same domain
def get_domain_hyperlinks_headless(driver, local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks_headless(driver, url)):
        clean_link = None
        # If the link is a URL, check if it is within the same domain
        if re.search(HTTP_URL_PATTERN, link):
            # Parse the URL and check if the domain is the same
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link

        # If the link is not a URL, check if it is a relative link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif link.startswith("#") or link.startswith("mailto:"):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)

    # Return the list of hyperlinks that are within the same domain
    return list(set(clean_links))

def preflight_url_validation(url, max_pages=100):
    # check url pattern otherwise trying adding https or http
    if not re.search(HTTP_URL_PATTERN, url):
        url = "https://" + url
    # check if url is valid
    local_domain = urlparse(url).netloc
    queue = deque([url])
    seen = set([url])
    links = []
    source_id = generate_uuid(8)
    while queue:
        link_id = generate_uuid(4)
        url = queue.pop()
        soup = BeautifulSoup(requests.get(url).text, "html.parser")
        text = soup.get_text()
        n_tokens = InferenceUtils.num_tokens_from_string(text)
        if ("You need to enable JavaScript to run this app" in text):
            pass
        else:
            links.append({"url": url, "js_required": False, "n_tokens": n_tokens, "content": text, "link_id": link_id})
        for link in get_domain_hyperlinks(local_domain, url):
            link = link.strip("/")
            if link not in seen:
                if len(seen) > max_pages:
                    return links 
                queue.append(link)
                seen.add(link)
    return {"source_id": source_id, "links": links} 

# Create a class to parse the HTML and get the hyperlinks
class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # Create a list to store the hyperlinks
        self.hyperlinks = []

    # Override the HTMLParser's handle_starttag method to get the hyperlinks
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # If the tag is an anchor tag and it has an href attribute, add the href attribute to the list of hyperlinks
        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])

# Function to get the hyperlinks from a URL
def get_hyperlinks(url):
    
    # Try to open the URL and read the HTML
    try:
        # Open the URL and read the HTML
        with urllib.request.urlopen(url) as response:
            # If the response is not HTML, return an empty list
            if not response.info().get('Content-Type').startswith("text/html"):
                return []
            # Decode the HTML
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []
    # Create the HTML Parser and then Parse the HTML to get hyperlinks
    parser = HyperlinkParser()
    parser.feed(html)
    return parser.hyperlinks

# Function to get the hyperlinks from a URL that are within the same domain
def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        # If the link is a URL, check if it is within the same domain
        if re.search(HTTP_URL_PATTERN, link):
            # Parse the URL and check if the domain is the same
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link

        # If the link is not a URL, check if it is a relative link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif link.startswith("#") or link.startswith("mailto:"):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)

    # Return the list of hyperlinks that are within the same domain
    return list(set(clean_links))

def crawl(url, user, source_id, max_tokens=50000):
    import time
    import tiktoken
    if not re.search(HTTP_URL_PATTERN, url):
        url = "https://" + url
    local_domain = urlparse(url).netloc
    queue = deque([url])
    seen = set([url])
    user_folder = os.path.join(os.getcwd(), 'users', user)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    if not os.path.exists(user_folder+'/files'):
        os.makedirs(user_folder+'/files')
    if not os.path.exists(user_folder+'/files/'+source_id):
        os.makedirs(user_folder+'/files/'+source_id)
    base = f'users/{user}/files/{source_id}/'
    summary = []
    tokenizer = tiktoken.get_encoding("cl100k_base")
    n_tokens = 0
    while queue:
        if n_tokens > max_tokens:
            return {'status': 'success', 'summary': summary, 'n_tokens': n_tokens, 'reason': 'excceeded max tokens'}
        url = queue.pop()
        fname = url.replace("https://", "").replace("http://", "").replace("/", "_")
        with open(base+fname+".txt","w") as f:
            # get url text with exponential backoff
            for i in range(5):
                try:
                    res = requests.get(url)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                    break
                except Exception as e:
                    print(e)
                    time.sleep(2**i)
            text = soup.get_text()
            if ("You need to enable JavaScript to run this app." in text):
                summary.append({"url": url, "is_crawled": False, "js_required": True})
            else:
                f.write(text)

            try:
                n_tokens += len(tokenizer.encode(text))
            except:
                pass

        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen:
                queue.append(link)
                seen.add(link)

    return {'status': 'success', 'reason': 'crawled', 'summary': summary, 'n_tokens': n_tokens}
