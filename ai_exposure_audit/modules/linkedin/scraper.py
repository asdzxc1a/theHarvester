import requests
import json
import os
import time # For potential rate limiting delays

# Attempt to import the API key from the core config
try:
    from ...core.config import PROXYCURL_API_KEY
except (ImportError, ValueError): 
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv() 
    PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")

# Correct Base URL for Proxycurl API
PROXYCURL_API_BASE_URL = "https://nubela.co/proxycurl.api" 

# Correct Endpoint for employee listing
EMPLOYEE_LIST_ENDPOINT = "/linkedin/company/employees/"

def get_company_employees(company_linkedin_url: str, max_employees: int = 10) -> list[dict]:
    """
    Fetches employee data for a given company using the Proxycurl API.

    Args:
        company_linkedin_url (str): The LinkedIn profile URL of the target company.
        max_employees (int): The maximum number of employees to fetch.
                             Fetches in pages of 10 (due to enrich_profiles='enrich' limit).

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains employee data.
    
    Raises:
        ValueError: If the API key is not configured or if JSON response is invalid.
        requests.exceptions.HTTPError: If the API request returns an error status code.
        requests.exceptions.RequestException: For other network-related issues.
    """
    if not PROXYCURL_API_KEY:
        raise ValueError("Proxycurl API key not configured. Please set PROXYCURL_API_KEY in your .env file.")

    headers = {
        'Authorization': f'Bearer {PROXYCURL_API_KEY}',
        'Accept': 'application/json' 
    }
    
    api_url = f"{PROXYCURL_API_BASE_URL}{EMPLOYEE_LIST_ENDPOINT}"
    
    all_employees_data = []
    current_page_size = 10 # As per documentation for enrich_profiles='enrich'
    next_page_cursor = None

    while len(all_employees_data) < max_employees:
        params = {
            'url': company_linkedin_url,
            'enrich_profiles': 'enrich',
            'page_size': str(current_page_size), # API expects string for page_size
            'employment_status': 'current',
        }
        if next_page_cursor:
            params['next_page'] = next_page_cursor
        
        # Determine how many more employees we need to fetch in this call
        remaining_needed = max_employees - len(all_employees_data)
        if remaining_needed < current_page_size:
            params['page_size'] = str(remaining_needed) # Adjust page_size for the last call if needed

        print(f"Fetching employees from Proxycurl: {api_url}")
        print(f"Parameters: {params}")
        print(f"API Key (first 5 chars): {PROXYCURL_API_KEY[:5]}...")

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=45) # Increased timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            
            data = response.json()

            # Extract employees from the current page
            current_page_employees = data.get('employees', [])
            if not isinstance(current_page_employees, list):
                print(f"Warning: Expected 'employees' to be a list, but got {type(current_page_employees)}. Response: {data}")
                # Handle cases where the API might return an error within a 200 OK response
                if isinstance(data, dict) and (data.get('error') or data.get('detail')):
                    error_detail = data.get('error', data.get('detail', 'Unknown API error in response'))
                    raise ValueError(f"Proxycurl API returned an error in response: {error_detail}")
                break # Stop if the structure is not as expected

            for item in current_page_employees:
                if not isinstance(item, dict):
                    print(f"Warning: Skipping non-dictionary item in employees list: {item}")
                    continue

                profile = item.get('profile')
                if not isinstance(profile, dict):
                    print(f"Warning: Skipping item with missing or invalid 'profile' field: {item}")
                    # Store what we can, or skip. For now, we need profile for name and headline.
                    all_employees_data.append({
                        'profile_url': item.get('profile_url', 'N/A'),
                        'full_name': 'N/A (Profile data missing)',
                        'job_title': 'N/A (Profile data missing)',
                        'raw_data': item
                    })
                    continue

                all_employees_data.append({
                    'profile_url': item.get('profile_url', 'N/A'),
                    'full_name': profile.get('full_name', 'N/A'),
                    'job_title': profile.get('headline', 'N/A'), # Using headline as job_title
                    'raw_data': item # Store the raw item for flexibility
                })

                if len(all_employees_data) >= max_employees:
                    break # Reached max_employees limit

            # Check for next page
            next_page_cursor = data.get('next_page')
            if not next_page_cursor or len(all_employees_data) >= max_employees:
                break # No more pages or max_employees reached

            # Optional: Add a small delay to be respectful to the API
            # time.sleep(1) 

        except requests.exceptions.HTTPError as http_err:
            error_message = f"HTTP error occurred: {http_err}"
            if http_err.response is not None:
                error_message += f" - Status: {http_err.response.status_code}, Response: {http_err.response.text[:500]}"
            print(error_message)
            # You might want to break or return partially collected data depending on requirements
            raise 
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            raise
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred with the request: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            response_text_snippet = response.text[:200] if 'response' in locals() and hasattr(response, 'text') else "N/A"
            print(f"Error decoding JSON response: {json_err} - Response snippet: {response_text_snippet}...")
            raise ValueError(f"Invalid JSON response from API: {json_err.msg}")
        except Exception as e: # Catch any other unexpected errors during processing
            print(f"An unexpected error occurred during employee processing: {type(e).__name__} - {e}")
            # Depending on severity, you might re-raise or break
            raise

    return all_employees_data[:max_employees] # Ensure we don't exceed max_employees


if __name__ == '__main__':
    print("Running scraper.py directly for testing with real Proxycurl API details...")

    if not PROXYCURL_API_KEY:
        print("CRITICAL: PROXYCURL_API_KEY is not set.")
        print("Please ensure a .env file exists in the project root (ai_exposure_audit/)")
        print("with your key, or that the variable is set in your environment.")
        print("Example .env content in project root:\nPROXYCURL_API_KEY=your_actual_api_key_here")
        print("Without an API key, the test cannot run against the live API.")
    else:
        print(f"Proxycurl API Key loaded (first 5 chars): {PROXYCURL_API_KEY[:5]}...")
        
        # Test with a known company LinkedIn URL.
        # You can replace this with any company's LinkedIn URL for testing.
        # e.g., "https://www.linkedin.com/company/google"
        #       "https://www.linkedin.com/company/microsoft"
        #       "https://www.linkedin.com/company/linkedin" (Proxycurl's example)
        test_company_url = "https://www.linkedin.com/company/linkedin" 
        num_employees_to_fetch = 15 # Test fetching more than one page

        print(f"\nAttempting to fetch {num_employees_to_fetch} employees for: {test_company_url}")
        
        try:
            employees = get_company_employees(test_company_url, max_employees=num_employees_to_fetch)
            
            if employees:
                print(f"\nSuccessfully fetched {len(employees)} employees (max {num_employees_to_fetch} requested):")
                for i, emp in enumerate(employees):
                    print(f"  Employee {i+1}:")
                    print(f"    Full Name: {emp.get('full_name')}")
                    print(f"    Job Title (Headline): {emp.get('job_title')}")
                    print(f"    Profile URL: {emp.get('profile_url')}")
                    # print(f"    Raw Data Snippet: {str(emp.get('raw_data'))[:100]}...") # Uncomment for debugging
            elif employees == []:
                 print("API call completed, but no employees were extracted. This could be due to:")
                 print("  1. The company having no public employee data fitting the query parameters.")
                 print("  2. An issue with the API key (e.g., invalid, expired, or out of credits).")
                 print("  3. The specific company URL not being found or processed correctly by Proxycurl.")
                 print("  4. An API error message returned in a 200 OK response that was not caught.")
            else: 
                print("No employees found, or an unexpected return value from get_company_employees.")

        except ValueError as ve:
            print(f"Error: {ve}")
        except requests.exceptions.HTTPError as he:
             print(f"API Call HTTP Error: {he}")
             if he.response is not None:
                 print(f"Response Status: {he.response.status_code}")
                 try:
                     print(f"Response Body: {he.response.json()}") # Try to print JSON error if possible
                 except json.JSONDecodeError:
                     print(f"Response Body (text): {he.response.text[:500]}")
        except requests.exceptions.RequestException as re:
            print(f"API Call Failed: {re}")
        except Exception as e:
            print(f"An unexpected critical error occurred during testing: {type(e).__name__} - {e}")

        print("\n--- End of test ---")
        print("If the test failed, check your PROXYCURL_API_KEY, network connection,")
        print("and the Proxycurl dashboard for any API usage issues or errors.")
