from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import json
import time


def scrape_naukri_jobs_simple(url, location, max_results=20, debug=False):
    """
    Simpler fallback scraper that uses requests + BeautifulSoup only.
    This is used in environments (like Railway) where Chrome is not available.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        if debug:
            print(f"[Fallback] Fetching URL via requests: {url}")

        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        if debug:
            print(f"[Fallback] Error fetching URL: {e}")
        return []

    jobs = []
    seen_urls = set()

    # Heuristic: job links usually contain "job-listings" or related patterns in the path
    job_links = soup.find_all(
        "a",
        href=lambda x: x
        and (
            "/job-listings" in x
            or "/job-" in x
            or "/job/" in x
        ),
    )[: max_results * 3]

    if debug:
        print(f"[Fallback] Found {len(job_links)} potential job links")

    for link in job_links:
        try:
            job_url = link.get("href", "")
            if not job_url:
                continue

            if not job_url.startswith("http"):
                job_url = f"https://www.naukri.com{job_url}"

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            title = link.get("title") or link.text.strip()
            if not title or len(title) < 3:
                continue

            parent = link.find_parent(["article", "div"]) or soup
            company = "Not specified"
            experience = "Not specified"
            salary = "Not disclosed"
            job_location = location

            # Company name
            comp_elem = parent.find(
                ["a", "span", "div"],
                class_=lambda c: c and "comp" in str(c).lower(),
            )
            if comp_elem:
                company = comp_elem.text.strip()

            # Other metadata
            for span in parent.find_all("span"):
                text = span.text.strip()
                lower = text.lower()
                if any(x in lower for x in ["yr", "year", "exp"]):
                    experience = text
                elif any(x in lower for x in ["lakh", "crore", "salary", "pa"]):
                    salary = text
                elif any(
                    city in lower
                    for city in [
                        "bangalore",
                        "mumbai",
                        "delhi",
                        "hyderabad",
                        "pune",
                        "chennai",
                        "gurgaon",
                        "noida",
                    ]
                ):
                    job_location = text

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "experience": experience,
                    "salary": salary,
                    "location": job_location,
                    "url": job_url,
                    "platform": "Naukri",
                }
            )

            if len(jobs) >= max_results:
                break

        except Exception as e:
            if debug:
                print(f"[Fallback] Error parsing job link: {e}")
            continue

    if debug:
        print(f"[Fallback] Returning {len(jobs)} jobs")

    return jobs


def scrape_naukri_jobs(keywords, location, max_results=20, debug=False):
    """Naukri scraper using Selenium to handle JavaScript-rendered content."""

    search_query = keywords.lower().replace(" ", "-")
    url = f"https://www.naukri.com/{search_query}-jobs-in-{location.lower()}"

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        if debug:
            print(f"Fetching URL: {url}")

        # Initialize Chrome driver
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as chrome_error:
            # In environments without Chrome (e.g. Railway), fall back to requests-based scraping
            if debug:
                print("Chrome WebDriver failed, falling back to simple scraper.")
                print(f"Chrome error: {chrome_error}")
            return scrape_naukri_jobs_simple(url, location, max_results, debug)
        
        # Navigate to the page
        driver.get(url)
        
        if debug:
            print(f"Page loaded. Waiting for job listings...")
        
        # Wait for job listings to load (try multiple selectors)
        wait = WebDriverWait(driver, 20)
        
        # Wait for shimmer/loading to disappear and actual content to load
        if debug:
            print("Waiting for page to fully load...")
        
        # Wait a bit for initial page load
        time.sleep(5)
        
        # Try to wait for actual job content (not shimmer)
        try:
            # Wait for job title links to appear (actual content, not shimmer)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[title*='job'], a[href*='/job'], article[class*='tuple']:not([class*='shimmer'])")))
            if debug:
                print("Job listings detected!")
            # Give additional time for all jobs to render
            time.sleep(3)
        except:
            # Give it more time for JavaScript to render
            if debug:
                print("Waiting additional time for content to load...")
            time.sleep(5)
        
        # Try to find job listings using Selenium directly (more reliable for dynamic content)
        jobs = []
        
        # Try multiple CSS selectors to find job listings
        job_selectors = [
            "article[class*='tuple']:not([class*='shimmer'])",
            "div[class*='tuple']:not([class*='shimmer'])",
            "a[href*='/job']",
            "[data-job-id]",
            "article[class*='job']",
        ]
        
        job_elements = []
        for selector in job_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # Filter out shimmer/loading elements
                job_elements = [e for e in elements if 'shimmer' not in e.get_attribute('class') or '']
                if len(job_elements) > 0:
                    if debug:
                        print(f"Found {len(job_elements)} job elements using selector: {selector}")
                    break
            except:
                continue
        
        if len(job_elements) == 0:
            # Fallback: Get page source and parse with BeautifulSoup
            if debug:
                print("Trying BeautifulSoup fallback...")
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try finding job links
            job_links = soup.find_all('a', href=lambda x: x and '/job' in x)
            if debug:
                print(f"Found {len(job_links)} job links in HTML")
            
            # Extract unique jobs from links
            seen_urls = set()
            for link in job_links[:max_results * 2]:  # Get more to account for duplicates
                try:
                    job_url = link.get('href', '')
                    if not job_url.startswith('http'):
                        job_url = f'https://www.naukri.com{job_url}'
                    
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    
                    # Try to find title
                    title = link.get('title', '') or link.text.strip()
                    if not title:
                        continue
                    
                    # Try to find parent container for other details
                    parent = link.find_parent(['article', 'div'])
                    company = 'Not specified'
                    experience = 'Not specified'
                    salary = 'Not disclosed'
                    job_location = location
                    
                    if parent:
                        # Try to find company
                        company_elem = parent.find(['a', 'span'], class_=lambda x: x and 'comp' in str(x).lower())
                        if company_elem:
                            company = company_elem.text.strip()
                        
                        # Try to find experience, salary, location
                        for span in parent.find_all('span'):
                            text = span.text.strip().lower()
                            if 'yr' in text or 'year' in text or 'exp' in text:
                                experience = span.text.strip()
                            elif 'lakh' in text or 'crore' in text or 'salary' in text:
                                salary = span.text.strip()
                            elif any(city in text for city in ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai']):
                                job_location = span.text.strip()
                    
                    jobs.append({
                        'title': title,
                        'company': company,
                        'experience': experience,
                        'salary': salary,
                        'location': job_location,
                        'url': job_url,
                        'platform': 'Naukri'
                    })
                    
                    if len(jobs) >= max_results:
                        break
                except:
                    continue
            
            return jobs
        
        # Extract job information from Selenium elements
        seen_urls = set()
        skipped_count = 0
        for job_elem in job_elements[:max_results * 3]:  # Get more to account for duplicates and invalid entries
            try:
                # Get the HTML of this element and parse it
                elem_html = job_elem.get_attribute('outerHTML')
                soup_elem = BeautifulSoup(elem_html, 'html.parser')
                
                # Try to find title from link
                title = ''
                job_url = None
                
                # Look for job title link - try multiple strategies
                title_link = (soup_elem.find('a', title=True) or 
                              soup_elem.find('a', href=lambda x: x and '/job' in str(x)) or
                              soup_elem.find('a', class_=lambda x: x and 'title' in str(x).lower()) or
                              soup_elem.find('a'))
                
                if title_link:
                    title = title_link.get('title', '').strip() or title_link.text.strip()
                    job_url = title_link.get('href', '')
                
                # If no title found, try other methods
                if not title:
                    h2 = soup_elem.find('h2')
                    if h2:
                        title = h2.text.strip()
                
                if not title:
                    # Try getting first meaningful text from the element
                    all_text = job_elem.text.strip()
                    if all_text:
                        # Get first line that's not empty and has some content
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        if lines:
                            title = lines[0]
                            # If first line is too short, try second
                            if len(title) < 5 and len(lines) > 1:
                                title = lines[1]
                
                if not title or len(title) < 3:
                    skipped_count += 1
                    if debug and skipped_count <= 3:  # Only show first few skipped items
                        print(f"Skipping job element {skipped_count}: No valid title found")
                    continue
                
                # Try to find company - multiple strategies
                company = 'Not specified'
                company_elem = (soup_elem.find('a', class_=lambda x: x and 'comp' in str(x).lower()) or
                               soup_elem.find('span', class_=lambda x: x and 'comp' in str(x).lower()) or
                               soup_elem.find('div', class_=lambda x: x and 'comp' in str(x).lower()))
                
                if company_elem:
                    company = company_elem.text.strip()
                else:
                    # Try to find company from text patterns (usually appears after title)
                    all_text = job_elem.text.strip()
                    if all_text:
                        lines = [line.strip() for line in all_text.split('\n') if line.strip() and len(line.strip()) > 2]
                        # Company usually appears in second or third line
                        if len(lines) > 1:
                            potential_company = lines[1]
                            # Skip if it looks like experience or location
                            if not any(x in potential_company.lower() for x in ['yr', 'year', 'exp', 'lakh', 'crore', 'pa', 'bangalore', 'mumbai', 'delhi']):
                                company = potential_company
                
                # Try to find experience, salary, location from spans
                experience = 'Not specified'
                salary = 'Not disclosed'
                job_location = location
                
                for span in soup_elem.find_all('span'):
                    text = span.text.strip()
                    text_lower = text.lower()
                    
                    if 'yr' in text_lower or 'year' in text_lower or 'exp' in text_lower:
                        if experience == 'Not specified':
                            experience = text
                    elif 'lakh' in text_lower or 'crore' in text_lower or 'salary' in text_lower or 'pa' in text_lower:
                        if salary == 'Not disclosed':
                            salary = text
                    elif any(city in text_lower for city in ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai', 'gurgaon', 'noida']):
                        job_location = text
                
                # Fix job URL
                if job_url:
                    if not job_url.startswith('http'):
                        job_url = f'https://www.naukri.com{job_url}'
                else:
                    # Try to find URL from data attributes or other links
                    data_url = job_elem.get_attribute('data-url') or job_elem.get_attribute('href')
                    if data_url:
                        job_url = data_url if data_url.startswith('http') else f'https://www.naukri.com{data_url}'
                    else:
                        job_url = 'N/A'
                
                # Skip duplicates
                if job_url in seen_urls or job_url == 'N/A':
                    continue
                seen_urls.add(job_url)
                
                jobs.append({
                    'title': title,
                    'company': company,
                    'experience': experience,
                    'salary': salary,
                    'location': job_location,
                    'url': job_url,
                    'platform': 'Naukri'
                })
                
                if len(jobs) >= max_results:
                    break
                
            except Exception as e:
                if debug:
                    print(f"Error parsing job: {str(e)}")
                skipped_count += 1
                continue
        
        if debug:
            print(f"\nExtraction Summary:")
            print(f"  Total elements found: {len(job_elements)}")
            print(f"  Successfully extracted: {len(jobs)}")
            print(f"  Skipped (no title/duplicates/errors): {skipped_count}")
        
        return jobs
    
    except Exception as e:
        if debug:
            print(f"Error: {str(e)}")
        return []
    
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    results = scrape_naukri_jobs('Senior Product Manager', 'Bangalore', 10, debug=True)
    print(f"\nFound {len(results)} jobs")
    if len(results) > 0:
        print("\nSample jobs:")
        print(json.dumps(results[:2], indent=2))
    else:
        print("\nNo jobs found. Check debug_response.html to see what was returned.")
