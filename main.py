from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs, urljoin
import io
import csv

app = FastAPI()

# Global in-memory storage to keep track of the last scraped batch for downloading
last_scraped_results = []

class SearchRequest(BaseModel):
    query: str

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Scraper Dashboard</title>
    <script src="https://tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen p-4">
    <div class="max-w-xl mx-auto space-y-6">
        <header class="text-center py-6">
            <h1 class="text-2xl font-bold text-green-400">🚀 Free Lead Scraper</h1>
            <p class="text-gray-400 text-sm mt-1">Find live business leads & emails instantly (No API Keys)</p>
        </header>

        <div class="bg-gray-800 p-4 rounded-xl shadow-lg space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">Search Query</label>
                <input type="text" id="queryInput" placeholder="e.g., Landscaping in Austin Texas" 
                    class="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-400">
            </div>
            <button onclick="runScraper()" id="searchBtn"
                class="w-full bg-green-500 hover:bg-green-600 text-gray-950 font-bold py-3 rounded-lg transition">
                Start Scraping
            </button>
        </div>

        <div id="resultsSection" class="space-y-4 hidden">
            <div class="flex justify-between items-center">
                <h2 class="text-lg font-semibold text-gray-200">Results (<span id="count">0</span>)</h2>
                <a id="downloadBtn" href="/download-csv" 
                    class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2 px-4 rounded-lg transition hidden">
                    📥 Download CSV
                </a>
            </div>
            <div id="resultsList" class="space-y-3"></div>
        </div>
    </div>

    <script>
        async function runScraper() {
            const query = document.getElementById('queryInput').value;
            const btn = document.getElementById('searchBtn');
            const downloadBtn = document.getElementById('downloadBtn');
            if (!query) return alert('Please enter a search query');

            btn.innerText = 'Scraping live data & sites...';
            btn.disabled = true;
            downloadBtn.classList.add('hidden');

            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                const data = await response.json();
                
                document.getElementById('count').innerText = data.leads_found;
                const listDiv = document.getElementById('resultsList');
                listDiv.innerHTML = '';

                if (data.results.length === 0) {
                    listDiv.innerHTML = '<p class="text-gray-400 text-center">No live leads found. Try a more specific local keyword (e.g. city + niche).</p>';
                } else {
                    // Show download button only if real leads exist
                    downloadBtn.classList.remove('hidden');
                }

                data.results.forEach(lead => {
                    listDiv.innerHTML += `
                        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 space-y-2">
                            <h3 class="font-bold text-white text-lg">${lead.business_name}</h3>
                            <p class="text-sm text-gray-300">📞 ${lead.phone}</p>
                            <p class="text-sm text-green-300">📧 ${lead.email}</p>
                            <a href="${lead.website}" target="_blank" class="text-xs text-green-400 underline block truncate">${lead.website}</a>
                        </div>
                    `;
                });

                document.getElementById('resultsSection').classList.remove('hidden');
            } catch (err) {
                alert('Something went wrong during scraping!');
            } finally {
                btn.innerText = 'Start Scraping';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

def extract_clean_url(ddg_href):
    try:
        parsed = urlparse(ddg_href)
        if 'duckduckgo.com' in parsed.netloc and parsed.query:
            query_params = parse_qs(parsed.query)
            if 'uddg' in query_params:
                return query_params['uddg'][0]
    except Exception:
        pass
    return ddg_href

def scan_text_for_contacts(html_source):
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html_source)
    valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'))]
    
    phones = re.findall(r"\(?\d{3}\)?[-.\s]?\d{3][-.\s]?\d{4}", html_source)
    
    return list(set(valid_emails)), list(set(phones))

def deep_scrape_website(base_url, headers):
    email_list, phone_list = [], []
    if not base_url or base_url.startswith('#'):
        return "Not found", "Not found"
        
    try:
        res = requests.get(base_url, headers=headers, timeout=4)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            email_list, phone_list = scan_text_for_contacts(res.text)
            
            if not email_list or not phone_list:
                contact_href = None
                for a_tag in soup.find_all('a', href=True):
                    link_text = a_tag.get_text().lower()
                    link_href = a_tag['href'].lower()
                    
                    if any(keyword in link_text or keyword in link_href for keyword in ['contact', 'about', 'reach', 'info']):
                        contact_href = a_tag['href']
                        break
                
                if contact_href:
                    full_contact_url = urljoin(base_url, contact_href)
                    contact_res = requests.get(full_contact_url, headers=headers, timeout=4)
                    if contact_res.status_code == 200:
                        c_emails, c_phones = scan_text_for_contacts(contact_res.text)
                        email_list.extend(c_emails)
                        phone_list.extend(c_phones)
                        
    except Exception:
        pass
        
    final_email = ", ".join(list(set(email_list))) if email_list else "Not found"
    final_phone = ", ".join(list(set(phone_list))) if phone_list else "Not found"
    return final_email, final_phone

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT

@app.post("/scrape")
def trigger_scrape(data: SearchRequest):
    global last_scraped_results
    query = data.query
    scraped_leads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        # Appending 'website' forces the search engine to index raw business landing pages
        search_url = f"https://duckduckgo.com{requests.utils.quote(query + ' website')}"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', class_='result', limit=10) # Scrapes top 10 positions
            
            for res in results:
                title_tag = res.find('a', class_='result__title')
                if title_tag:
                    name = title_tag.get_text().strip()
                    raw_link = title_tag.get('href', '#')
                    clean_url = extract_clean_url(raw_link)
                    
                    # Bypass directories so you only visit real local business assets
                    if any(x in clean_url for x in ['yelp.com', 'facebook.com', 'tripadvisor.com', 'instagram.com', 'linkedin.com', 'yellowpages.com']):
                        continue
                        
                    email, phone = deep_scrape_website(clean_url, headers)
                    
                    scraped_leads.append({
                        "business_name": name,
                        "phone": phone,
                        "email": email,
                        "website": clean_url
                    })
    except Exception as e:
        print(f"Error executing scraper: {e}")

    # Explicitly caching real live hits only (No demo variables)
    last_scraped_results = scraped_leads

    return {
        "query": query,
        "leads_found": len(scraped_leads),
        "results": scraped_leads
    }

@app.get("/download-csv")
def download_csv():
    """Generates and streams a formatted CSV spreadsheet file containing active leads data."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Define fields header matrix row
    writer.writerow(["Business Name", "Phone Number", "Email Address", "Website URL"])
    
    # Populate rows mapping dictionary keys 
    for lead in last_scraped_results:
        writer.writerow([
            lead["business_name"], 
            lead["phone"], 
            lead["email"], 
            lead["website"]
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scraped_leads.csv"}
    )
