from flask import Flask, request, jsonify
from flask_cors import CORS
from naukri_scrapper import scrape_naukri_jobs, apply_to_naukri_job
import os

app = Flask(__name__)
CORS(app)


@app.route("/scrape", methods=["POST"])
def scrape():
    """API endpoint to scrape jobs from Naukri based on keywords and location."""
    data = request.json or {}
    keywords = data.get("keywords", "Product Manager")
    location = data.get("location", "Mumbai")
    max_results = data.get("max_results", 20)

    print("=== /scrape called ===")
    print("Incoming data:", data)

    jobs = scrape_naukri_jobs(keywords, location, max_results, debug=True)
    print(
        f"Scrape finished. keywords={keywords!r}, "
        f"location={location!r}, count={len(jobs)}"
    )

    return jsonify(
        {
            "success": True,
            "count": len(jobs),
            "jobs": jobs,
        }
    )


@app.route("/apply", methods=["POST"])
def apply():
    """
    API endpoint to apply to a single Naukri job URL.

    Expects JSON body:
    {
      "job_url": "...",
      "cover_letter": "..."  # optional
    }

    NOTE: This is intended to run on your local machine where Selenium/Chrome
    are available. Do not expose publicly without proper auth.
    """

    data = request.json or {}
    job_url = data.get("job_url")
    cover_letter = data.get("cover_letter")

    print("=== /apply called ===")
    print("Incoming data:", data)

    if not job_url:
        return jsonify({"success": False, "error": "job_url is required"}), 400

    email = os.getenv("NAUKRI_EMAIL")
    password = os.getenv("NAUKRI_PASSWORD")

    if not email or not password:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "NAUKRI_EMAIL and NAUKRI_PASSWORD env vars are required",
                }
            ),
            500,
        )

    try:
        result = apply_to_naukri_job(
            job_url=job_url,
            email=email,
            password=password,
            cover_letter=cover_letter,
            debug=True,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        print("Apply error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)