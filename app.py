from flask import Flask, request, jsonify
from flask_cors import CORS
from naukri_scrapper import scrape_naukri_jobs
import os

app = Flask(__name__)
CORS(app)

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json or {}
    keywords = data.get('keywords', 'Product Manager')
    location = data.get('location', 'Mumbai')
    max_results = data.get('max_results', 20)

    print("=== /scrape called ===")
    print("Incoming data:", data)

    jobs = scrape_naukri_jobs(keywords, location, max_results, debug=True)
    print(f"Scrape finished. keywords={keywords!r}, location={location!r}, count={len(jobs)}")

    return jsonify({
        'success': True,
        'count': len(jobs),
        'jobs': jobs,
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)