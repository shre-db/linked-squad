__module_name__ = "profiles"

import os
import json
from .apify_scraper import linkedin_scraper


mock_linkedin_urls = {
    "johnsmith": "https://www.linkedin.com/in/johnsmith",
    "alicejohnson": "https://www.linkedin.com/in/alicejohnson",
    "boblee": "https://www.linkedin.com/in/boblee",
    "janedoe": "https://www.linkedin.com/in/janedoe",
    "arjunsrivastava": "https://www.linkedin.com/in/arjun-srivastava-ml/",
}
    

profile_a = {
    "name": "John Smith",
    "about": "Experienced software engineer with a passion for AI and machine learning.",
    "experience": [
        {"title": "Software Engineer", "company": "Tech Innovations", "description": "Developed scalable applications."},
        {"title": "AI Research Intern", "company": "Future Tech Labs", "description": "Worked on NLP models."}
    ],
    "skills": ["Python", "Machine Learning", "Cloud Computing"]
}

profile_b = {
    "name": "Alice Johnson",
    "about": "Marketing specialist with expertise in digital campaigns and brand strategy.",
    "experience": [
        {"title": "Marketing Manager", "company": "Brand Builders", "description": "Led successful marketing campaigns."},
        {"title": "Content Strategist", "company": "Creative Minds", "description": "Developed content strategies for clients."}
    ],
    "skills": ["Digital Marketing", "SEO", "Content Creation"]
}

profile_c = {
    "name": "Bob Lee",
    "about": "Financial analyst with a strong background in data analysis and investment strategies.",
    "experience": [
        {"title": "Financial Analyst", "company": "Wealth Advisors", "description": "Analyzed market trends and investment opportunities."},
        {"title": "Junior Analyst", "company": "Finance Corp", "description": "Assisted in financial reporting and forecasting."}
    ],
    "skills": ["Financial Analysis", "Excel", "Data Visualization"]
}

profile_d = {
    "name": "Jane Doe",
    "about": "Aspiring data scientist with strong foundations in ML and Python.",
    "experience": [
        {"title": "Data Analyst", "company": "Acme Corp", "description": "Worked on dashboards and reporting."}
    ],
    "skills": ["Python", "SQL", "Data Visualization"]
}

# Load from json file if available
try:
    # Load files and create a dictionary of profiles
    local_profiles = {}
    linkedin_dir = "linkedin"
    json_files = [f for f in os.listdir(linkedin_dir) if f.endswith('.json')]
    for file in json_files:
        with open(os.path.join(linkedin_dir, file), "r") as f:
            profile_data = json.load(f)
            profile_name = file.split('.')[0]
            local_profiles[profile_name] = profile_data
except FileNotFoundError:
    print("Mock profiles JSON file not found, using default profiles.")


def get_mock_profile(linkedin_url: str) -> dict:
    if "arjun-srivastava-ml" in linkedin_url:
        return local_profiles.get("linkedin_data_arjun_srivastava", {})
    elif "michael-rodriguez-cfa" in linkedin_url:
        return local_profiles.get("linkedin_data_michael_rodriguez", {})
    elif "sarah-chen-architect" in linkedin_url:
        return local_profiles.get("linkedin_data_sarah_chen", {})
    elif "johnsmith" in linkedin_url:
        return profile_a
    elif "alicejohnson" in linkedin_url:
        return profile_b
    elif "boblee" in linkedin_url:
        return profile_c
    elif "janedoe" in linkedin_url:
        return profile_d
    else:
        return {
            "name": "Unknown User",
            "about": "No profile information available.",
            "experience": [],
            "skills": []
        }

def get_profile(linkedin_url: str, linkedin_name: str) -> dict:
    """
    Loads a LinkedIn profile from a mock JSON file or scrapes it if not available.
    
    Args:
        linkedin_url (str): The LinkedIn profile URL.
        
    Returns:
        dict: Profile data.
    """
    if not linkedin_url:
        raise ValueError("LinkedIn URL cannot be empty.")
    
    # List all json files in the linkedin directory
    import os
    linkedin_dir = "linkedin"
    json_files = [f for f in os.listdir(linkedin_dir) if f.endswith('.json')]

    # Check if the profile already exists in the mock directory
    for file in json_files:
        if linkedin_name in file:
            try:
                with open(os.path.join(linkedin_dir, file), "r") as f:
                    profile_data = json.load(f)
                    print(f"File exists locally! Loading... : {file}")
                return profile_data
            except Exception as e:
                print(f"Error loading profile from file: {e}")
                return get_mock_profile(linkedin_url)
    # If not found, scrape the profile
    try:
        linkedin_name = linkedin_url.split("/")[-2]
        linkedin_scraper(linkedin_url, linkedin_name=linkedin_name)
        with open(f"linkedin/mock_profile_{linkedin_name}.json", "r") as f:
            profile_data = json.load(f)
        return profile_data
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return {
            "name": "Unknown User",
            "about": "No profile information available.",
            "experience": [],
            "skills": []
        }
    