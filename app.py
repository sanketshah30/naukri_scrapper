from flask import Flask, request, jsonify
from flask_cors import CORS
from naukri_scrapper import scrape_naukri_jobs

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'Naukri Scraper API',
        'endpoints': {
            '/health': 'GET - Check API health status',
            '/scrape': 'POST - Scrape jobs from Naukri',
        },
        'usage': {
            '/scrape': {
                'method': 'POST',
                'body': {
                    'keywords': 'Job title (e.g., "Product Manager")',
                    'location': 'Location (e.g., "Mumbai", "Bangalore")',
                    'max_results': 'Maximum number of jobs to return (default: 20)'
                },
                'example': {
                    'keywords': 'Product Manager',
                    'location': 'Mumbai',
                    'max_results': 10
                }
            }
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    keywords = data.get('keywords', 'Product Manager')
    location = data.get('location', 'Mumbai')
    max_results = data.get('max_results', 20)
    
    jobs = scrape_naukri_jobs(keywords, location, max_results)
    
    return jsonify({
        'success': True,
        'count': len(jobs),
        'jobs': jobs
    })

import os

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)