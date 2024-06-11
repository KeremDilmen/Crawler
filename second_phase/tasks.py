import requests
import json
from celery_config import app

url = "https://ranking.glassdollar.com/graphql"
headers = {
    "Content-Type": "application/json"
}

@app.task
def fetch_companies(page):
    corporates_query = """
    query Corporates($filters: CorporateFilters, $page: Int) {
      corporates(filters: $filters, page: $page) {
        rows {
          id
          name
          description
          logo_url
          hq_city
          hq_country
          website_url
          linkedin_url
          twitter_url
          startup_partners_count
        }
        count
      }
    }
    """
    filters = {
        "hq_city": [],
        "industry": []
    }
    response = requests.post(url, json={"query": corporates_query, "variables": {"filters": filters, "page": page}}, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data for page {page}: {response.status_code}")
        return None
    response_json = response.json()
    if "data" not in response_json or "corporates" not in response_json["data"]:
        print(f"Unexpected response structure for page {page}")
        return None
    return response_json["data"]["corporates"]

@app.task
def fetch_all_companies():
    all_companies = []
    page = 1
    while True:
        data = fetch_companies(page)
        if not data or not data["rows"]:
            break
        all_companies.extend(company["id"] for company in data["rows"])
        if len(all_companies) >= data["count"]:
            break
        page += 1
    return all_companies

@app.task
def fetch_enterprise_details(enterprise_id):
    payload_detail = {
        "variables": {"id": enterprise_id},
        "query": """
        query ($id: String!) {
            corporate(id: $id) {
                name
                description
                logo_url
                hq_city
                hq_country
                website_url
                linkedin_url
                twitter_url
                startup_partners_count
                startup_partners {
                    company_name
                    logo_url: logo
                    city
                    website
                    country
                    theme_gd
                }
                startup_themes
            }
        }
        """
    }
    response_detail = requests.post(url, headers=headers, json=payload_detail)
    data_detail = response_detail.json()
    if 'data' in data_detail and 'corporate' in data_detail['data']:
        return data_detail['data']['corporate']
    else:
        print(f"Error: Could not retrieve details for enterprise ID {enterprise_id}.")
        print("Response:", data_detail)
        return None

@app.task
def save_to_json(enterprise_details):
    with open('all_company_details.json', 'w') as json_file:
        json.dump(enterprise_details, json_file, indent=4)
    return "Data saved to enterprise_details.json"

@app.task
def run_analysis():
    import cluster
    return "Analysis complete"