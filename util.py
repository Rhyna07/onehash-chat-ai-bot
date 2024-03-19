from PyPDF2 import PdfReader
from docx import Document
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, SubElement
import trafilatura
from langchain_community.llms import OpenAI
import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
open_ai_api_key = os.getenv("OPEN_AI_API_KEY")  # Get OpenAI API key from .env file

def extract_text_from_pdf(pdf_file):
    text = ""
    with BytesIO(pdf_file.file.read()) as file:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(docx_file):
    text = ""
    with BytesIO(docx_file.file.read()) as file:
        doc = Document(file)
        for paragraph in doc.paragraphs:
            text += paragraph.text + '\n'
    return text

def extract_text_from_txt(txt_file):
    text = ""
    with BytesIO(txt_file.file.read()) as file:
        text = file.read().decode('utf-8')
    return text

def extract_text_from_url(url, open_ai_api_key=None):
    # Initialize webquery class with OpenAI API key
    web_query = WebQuery(open_ai_api_key)

    # Call the ingest method of the webquery class to process the URL
    result = web_query.ingest(url)

    # Return the result of processing the URL
    return result

class WebQuery:
    def __init__(self, open_ai_api_key=None):
        self.open_ai_api_key = open_ai_api_key
        self.processed_links = set() 

    def ingest(self, url: str) -> str:
        
        if url in self.processed_links:
            print(f"Link {url} has already been processed. Skipping.")
            return "Skipped"

        # Generate sitemap for the given URL
        sitemap_xml = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        self.crawl_and_append_to_sitemap(url, sitemap_xml, depth=2)

        # Extract links from the sitemap and fetch content
        links = [loc.text for loc in sitemap_xml.findall('.//loc')]

        for link in links:
            # Skip if the link has already been processed
            if link in self.processed_links:
                print(f"Link {link} has already been processed. Skipping.")
                continue

            result = trafilatura.extract(trafilatura.fetch_url(link))
            if result:
                self.processed_links.add(link)  # Mark link as processed
            else:
                print(f"Failed to extract content from {link}. Skipping.")

        return "Success"

    def crawl_and_append_to_sitemap(self, base_url, sitemap_xml, depth=2):
        if depth <= 0:
            return sitemap_xml

        urls_on_page, _ = self.get_urls_from_page(base_url)

        for url in urls_on_page:
            full_url = urljoin(base_url, url)
            url_element = SubElement(sitemap_xml, 'url')
            loc_element = SubElement(url_element, 'loc')
            loc_element.text = full_url

            # Recursively crawl and append links from the current URL
            self.crawl_and_append_to_sitemap(full_url, sitemap_xml, depth - 1)

    def get_urls_from_page(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extracting regular links
            urls = [a['href'] for a in soup.find_all('a', href=True) if not a['href'].startswith('mailto:')]

            return urls, []
        else:
            print(f"Failed to retrieve content from {url}. Status code: {response.status_code}")
            return [], []
