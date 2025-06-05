import os
from dotenv import load_dotenv
load_dotenv()

from apify_client import ApifyClient
import json
import time

class LinkedInScraper:
    def __init__(self, api_token):
        """Initialize the Apify client with your API token"""
        self.client = ApifyClient(api_token)
        
    def scrape_profile(self, linkedin_url, actor_id="curious_coder/linkedin-profile-scraper"):
        """
        Scrape a LinkedIn profile given its URL
        
        Args:
            linkedin_url (str): The LinkedIn profile URL to scrape
            actor_id (str): The Apify actor ID for LinkedIn scraping
            
        Returns:
            dict: Scraped profile data
        """
        try:
            # Configure the actor run input
            run_input = {
                "startUrls": [{"url": linkedin_url}],
                "proxyConfiguration": {"useApifyProxy": True},
                "maxRequestRetries": 3,
                "requestHandlerTimeoutSecs": 60
            }
            
            print(f"Starting scrape for: {linkedin_url}")
            
            # Run the actor
            run = self.client.actor(actor_id).call(run_input=run_input)
            print("Waiting for scrape to complete...")
            
            # Get the dataset items (results)
            dataset_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if dataset_items:
                profile_data = dataset_items[0]
                print("✅ Profile scraped successfully!")
                return profile_data
            else:
                print("❌ No data returned from scrape")
                return None
                
        except Exception as e:
            print(f"❌ Error during scraping: {str(e)}")
            return None
    
    def extract_key_info(self, profile_data):
        """
        Extract key information from scraped profile data
        
        Args:
            profile_data (dict): Raw profile data from Apify
            
        Returns:
            dict: Cleaned and structured profile information
        """
        if not profile_data:
            return None
            
        # Common fields that are usually available
        extracted_info = {
            "name": profile_data.get("name", ""),
            "headline": profile_data.get("headline", ""),
            "location": profile_data.get("location", ""),
            "summary": profile_data.get("summary", ""),
            "company": profile_data.get("company", ""),
            "position": profile_data.get("position", ""),
            "connections": profile_data.get("connectionsCount", ""),
            "experience": profile_data.get("experience", []),
            "education": profile_data.get("education", []),
            "skills": profile_data.get("skills", []),
            "profile_url": profile_data.get("url", ""),
            "profile_image": profile_data.get("profilePicture", "")
        }
        
        return extracted_info

# Usage example
def linkedin_scraper(linkedin_url=None, linkedin_name=None):
    # Set your Apify API token (get this from your Apify console)
    API_TOKEN = os.getenv("APIFY_API_TOKEN")
    
    # Initialize the scraper
    scraper = LinkedInScraper(API_TOKEN)
    
    if not linkedin_url:
        linkedin_url = "https://www.linkedin.com/in/shreyas-bangera-aa8012271/"

    # Scrape single profile
    print("=== Single Profile Scraping ===")
    profile_data = scraper.scrape_profile(linkedin_url)
    
    if profile_data:
        # Extract key information
        clean_data = scraper.extract_key_info(profile_data)
        
        print("\n=== Extracted Profile Information ===")
        print(json.dumps(clean_data, indent=2))
        
        # Save to file
        with open(f"linkedin_profile_{linkedin_name}.json", "w") as f:
            json.dump(clean_data, f, indent=2)
        print(f"\nProfile data saved to linkedin_profile_{linkedin_name}.json")

if __name__ == "__main__":
    linkedin_scraper()
    