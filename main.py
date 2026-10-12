from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

# Modern, mobile-friendly frontend dashboard
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Scraper Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen p-4">
    <div class="max-w-xl mx-auto space-y-6">
        <header class="text-center py-6">
            <h1 class="text-2xl font-bold text-green-400">🚀 Map Lead Scraper</h1>
            <p class="text-gray-400 text-sm mt-1">Find business leads & emails instantly</p>
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
            <h2 class="text-lg font-semibold text-gray-200">Results (<span id="count">0</span>)</h2>
            <div id="resultsList" class="space-y-3"></div>
        </div>
    </div>

    <script>
        async function runScraper() {
            const query = document.getElementById('queryInput').value;
            const btn = document.getElementById('searchBtn');
            if (!query) return alert('Please enter a search query');

            btn.innerText = 'Scraping...';
            btn.disabled = true;

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

                data.results.forEach(lead => {
                    listDiv.innerHTML += `
                        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 space-y-2">
                            <h3 class="font-bold text-white text-lg">\${lead.business_name}</h3>
                            <p class="text-sm text-gray-300">📞 \${lead.phone}</p>
                            <p class="text-sm text-gray-300">📧 \${lead.email}</p>
                            <a href="\${lead.website}" target="_blank" class="text-xs text-green-400 underline block">Visit Website</a>
                        </div>
                    `;
                });

                document.getElementById('resultsSection').classList.remove('hidden');
            } catch (err) {
                alert('Something went wrong!');
            } finally {
                btn.innerText = 'Start Scraping';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT

@app.post("/scrape")
def trigger_scrape(data: SearchRequest):
    search_query = data.query
    
    # Placeholder mock leads (we will wire up the actual map/web scraping logic next!)
    found_leads = [
        {
            "business_name": "Austin Prime Landscaping",
            "phone": "+1-512-555-0143",
            "email": "info@austinprimelandscaping.com",
            "website": "https://example.com"
        },
        {
            "business_name": "Texas Green Lawns",
            "phone": "+1-512-555-8892",
            "email": "contact@texasgreenlawns.com",
            "website": "https://example.com"
        }
    ]
    
    return {
        "query": search_query,
        "leads_found": len(found_leads),
        "results": found_leads
    }
