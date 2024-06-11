import requests
import json
import time

# URL and headers for the GraphQL requests
url = "https://ranking.glassdollar.com/graphql"
headers = {
    "Content-Type": "application/json"
}

# Get the list of enterprises with their IDs
payload_list = {
    "operationName": "TopRankedCorporates",
    "variables": {},
    "query": """
    query TopRankedCorporates {
        topRankedCorporates {
            id
        }
    }
    """
}

response_list = requests.post(url, headers=headers, json=payload_list)
data_list = response_list.json()

if 'data' not in data_list or 'topRankedCorporates' not in data_list['data']:
    print("Error: Could not retrieve the list of enterprises.")
    print("Response:", data_list)
    exit(1)

enterprise_ids = [corporate['id'] for corporate in data_list['data']['topRankedCorporates']]

# Get detailed information for each enterprise
enterprise_details = []

for enterprise_id in enterprise_ids:
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
        enterprise_details.append(data_detail['data']['corporate'])
    else:
        print(f"Error: Could not retrieve details for enterprise ID {enterprise_id}.")
        print("Response:", data_detail)

    # Small delay to avoid hitting the server too rapidly
    time.sleep(1)

# Save the detailed information as JSON
with open('enterprise_details.json', 'w') as json_file:
    json.dump(enterprise_details, json_file, indent=4)

print("Data saved to enterprise_details.json")
