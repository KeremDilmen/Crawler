from celery import group
from tasks import fetch_all_companies, fetch_enterprise_details, save_to_json

def main():
    try:
        # Fetch the list of all company IDs
        enterprise_ids = fetch_all_companies()
        
        # Create a group of tasks to fetch details for each enterprise
        tasks = group(fetch_enterprise_details.s(enterprise_id) for enterprise_id in enterprise_ids)
        
        # Execute the group of tasks in parallel
        result = tasks.apply_async()

        # Wait for all tasks to finish and collect results
        enterprise_details = result.get()
        enterprise_details = [detail for detail in enterprise_details if detail]

        # Save the detailed information as JSON
        save_to_json.delay(enterprise_details)
        print("Data is being processed and saved to JSON.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

