"""
Xonra Search — standalone Flask app.

Drop this route + the template into your main Xonra app, or run this
file on its own to test the search page in isolation.

Run standalone:
    pip install flask requests --break-system-packages
    python app.py
    -> open http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import time
import requests
from config import SERPER_API_KEY

app = Flask(__name__)

SERPER_ENDPOINT = "https://google.serper.dev/search"
RESULTS_PER_PAGE = 10


@app.route("/")
def index():
    return render_template("search.html")


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    page = request.args.get("page", "1")

    if not query:
        return jsonify({"error": "Missing search query"}), 400

    if SERPER_API_KEY.startswith("PASTE_"):
        return jsonify({
            "error": "Search isn't configured yet — add your Serper API key in config.py."
        }), 500

    try:
        page = int(page)
    except ValueError:
        page = 1

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "page": page,
        "num": RESULTS_PER_PAGE,
    }

    start_time = time.time()
    try:
        resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=8)
    except requests.RequestException:
        return jsonify({"error": "Couldn't reach the search API. Try again."}), 502
    search_time = round(time.time() - start_time, 2)

    if resp.status_code == 403:
        return jsonify({"error": "Invalid or missing Serper API key. Double-check app.py."}), 403

    if resp.status_code == 429:
        return jsonify({"error": "Free query balance is used up. Check your credits at serper.dev."}), 429

    if resp.status_code != 200:
        return jsonify({"error": f"Search API error ({resp.status_code})."}), 502

    data = resp.json()

    items = []
    for item in data.get("organic", []):
        favicon = item.get("favicon") or ""
        items.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "displayLink": item.get("link", "").split("/")[2] if "//" in item.get("link", "") else item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "thumbnail": None,
            "favicon": favicon,
        })

    # Serper doesn't return a total-results count; estimate whether another
    # page is likely based on whether this page came back full.
    next_page = page + 1 if len(items) >= RESULTS_PER_PAGE else None
    prev_page = page - 1 if page > 1 else None

    return jsonify({
        "query": query,
        "searchTime": search_time,
        "items": items,
        "nextStart": next_page,
        "prevStart": prev_page,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
