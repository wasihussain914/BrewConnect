import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import requests
from dotenv import load_dotenv

# Load environment variables from env file
load_dotenv("api_key.env")  # Specify the custom env file name

# --- CONFIGURATION ---
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

TARGET_COMPANY = "Google"          # Your desired company
TARGET_UNIVERSITY = "Vanderbilt University" # Your university name
MAX_REQUESTS_PER_RUN = 10          # CRITICAL SAFETY LIMIT: Start small (5-10) and only run once per day.

# --- 1. SETUP: BROWSER INITIALIZATION (NO LOGIN) ---
def setup_browser():
    """Initializes the Brave browser using a separate automation profile."""
    options = Options()
    
    # Set the binary location to Brave browser
    options.binary_location = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
    
    # Create a unique automation profile directory
    automation_profile = os.path.join(
        os.path.expanduser("~"),
        "AppData\\Local\\BraveSoftware\\Automation_Profile"
    )
    
    # Create the directory if it doesn't exist
    if not os.path.exists(automation_profile):
        os.makedirs(automation_profile)
    
    # Use the separate automation profile
    options.add_argument(f"--user-data-dir={automation_profile}")
    options.add_argument("--profile-directory=Default")
    
    # Add additional options for compatibility
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Disable notification prompts
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    
    # Let Selenium handle driver installation automatically
    driver = webdriver.Chrome(options=options)
    
    # Navigate to LinkedIn to ensure the session is active
    print("Checking LinkedIn session...")
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(20)  # Longer delay for profile loading
    #random.uniform(3, 5)
    if "login" in driver.current_url.lower():
        print("ERROR: Login check failed. Please log into LinkedIn in your Brave browser first.")
        driver.quit()
        raise Exception("Not Logged In")
    
    # Additional check for the nav bar which is only visible when logged in
    try:
        driver.find_element(By.ID, "global-nav")
        print("LinkedIn session verified - you are logged in.")
    except:
        print("ERROR: Could not verify LinkedIn session. Please check your login in Brave browser.")
        driver.quit()
        raise Exception("Session verification failed")
        
    print("Browser setup complete. LinkedIn session is active.")
    return driver

# --- 2. SEARCH & SCRAPE PROFILES ---
def search_and_get_profiles(driver, company, university):
    """Navigates to the company's people page with school filter."""
    
    # First navigate to the company page
    company_url = f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}/people/?facetSchool=4565"
    print(f"Opening {company}'s people page filtered for Vanderbilt alumni...")
    driver.get(company_url)
    
    # Wait for the page to load
    time.sleep(5)
    
    print("Looking for profile links...")
    
    # Scroll down a bit to load more content
    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(2)
    
    profile_data = []
    
    try:
        # Try to find profile links using the specific class
        profile_links = driver.find_elements(
            By.CSS_SELECTOR,
            "a.ember-view.link-without-visited-state.t-bold"
        )
        print(profile_links)
        
        print(f"Found {len(profile_links)} potential profile links")
        
        # Try clicking on the first few profiles
        for i, link in enumerate(profile_links[:3]):  # Start with just 3 profiles for testing
            try:
                print(f"Attempting to click profile {i+1}...")
                
                # Scroll the link into view
                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                time.sleep(1)
                
                # Get profile info before clicking
                url = link.get_attribute('href')
                name = link.text.strip()
                
                # Click the link
                link.click()
                time.sleep(3)  # Wait for profile to load
                
                # Store the profile info
                if name and url:
                    profile_data.append({'url': url, 'name': name})
                    print(f"Successfully clicked and stored profile: {name}")
                
                # Go back to the search results
                driver.back()
                time.sleep(2)
                
            except Exception as e:
                print(f"Error clicking profile: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error finding profiles: {str(e)}")
    
    print(f"Successfully processed {len(profile_data)} profiles")
    return profile_data

# --- 3. AI MESSAGE GENERATION ---
def generate_coffee_chat_note(name, company, university):
    """Calls the Claude API to generate a personalized connection note."""
    print(f"Generating note for {name}...")
    
    # Prompting for a professional, concise, and friendly note
    prompt = (
        f"Write a short, professional, and friendly LinkedIn connection request note (MAX 250 characters) "
        f"to {name}, who works at {company}. The sender is an alumnus/student from {university}. "
        f"The purpose is to request a brief virtual coffee chat to learn about their career path. "
        f"Start with 'Hi [First Name],'"
    )
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 150,
            "messages": [
                {"role": "system", "content": "You are a professional networking assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(CLAUDE_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        # Extract and clean up the message
        note = response.json()['content'][0]['text'].strip().replace('\n', ' ')
        
        # Replace the placeholder [First Name] with the actual name
        first_name = name.split()[0]
        note = note.replace("Hi [First Name],", f"Hi {first_name},")
        
        # Ensure it fits the 300 character limit for LinkedIn notes
        return note[:300]
    
    except Exception as e:
        print(f"Claude API call failed: {e}. Using fallback message.")
        return f"Hi {name.split()[0]}, I'm reaching out as a fellow {university} alumnus/student and admire your work at {company}. Would you be open to a quick virtual coffee chat?"

# --- 4. OUTREACH AND SAFETY MEASURES ---
def send_connection_request(driver, profile_url, name, message):
    """Navigates to a profile and sends the connection request with the note."""
    try:
        driver.get(profile_url)
        time.sleep(random.uniform(4, 6))

        # 1. Click the 'Connect' button (may appear as part of a drop-down menu)
        try:
            connect_button = driver.find_element(By.XPATH, "//button[contains(., 'Connect')]")
        except:
            # If 'Connect' is not immediately visible, it might be behind a 'More' button
            driver.find_element(By.XPATH, "//button[contains(., 'More')]").click()
            time.sleep(random.uniform(1, 2))
            connect_button = driver.find_element(By.XPATH, "//div[contains(., 'Connect')]/button") # Adjusted XPATH for the dropdown menu
            
        connect_button.click()
        time.sleep(random.uniform(1, 2))

        # 2. In the pop-up, click 'Add a note'
        add_note_button = driver.find_element(By.XPATH, "//button[contains(., 'Add a note')]")
        add_note_button.click()
        time.sleep(random.uniform(1, 2))

        # 3. Enter the personalized message
        text_area = driver.find_element(By.ID, "custom-message")
        text_area.send_keys(message)
        
        print(f"Note prepared for {name}: '{message}'")
        time.sleep(random.uniform(2, 3))

        # 4. Click 'Send'
        send_button = driver.find_element(By.XPATH, "//button[contains(., 'Send')]")
        send_button.click()
        time.sleep(random.uniform(3, 5)) # Longer delay after sending
        
        print(f"SUCCESS: Connection request sent to {name}.")

    except Exception as e:
        print(f"ERROR: Could not send request to {name}. The profile might already be connected, or the Connect button was not found. Error: {e}")
        # Log the URL to a file for manual follow-up
        with open("failed_requests.txt", "a") as f:
            f.write(f"{profile_url}, {name}, {TARGET_COMPANY}, {TARGET_UNIVERSITY}\n")
        pass

# --- MAIN EXECUTION ---
def main():
    if not CLAUDE_API_KEY:
        print("FATAL ERROR: Please set your CLAUDE_API_KEY environment variable.")
        return

    driver = setup_browser()
    
    try:
        # 1. Get the list of profiles
        profiles = search_and_get_profiles(driver, TARGET_COMPANY, TARGET_UNIVERSITY)
        
        # 2. Iterate and send requests
        for profile in profiles:
            name = profile['name']
            url = profile['url']
            
            # # Generate personalized note
            # note = generate_coffee_chat_note(name, TARGET_COMPANY, TARGET_UNIVERSITY)
            
            # # Send the connection request
            # send_connection_request(driver, url, name, note)
            
            # # CRITICAL: Add a randomized delay to avoid LinkedIn detection
            # delay = random.uniform(45, 120) # Delay between 45 and 120 seconds (1.5 - 2 minutes)
            # print(f"Pausing for {round(delay, 2)} seconds before processing the next profile...")
            # time.sleep(delay)

    finally:
        print("Automation finished. Closing browser.")
        driver.quit()

if __name__ == "__main__":
    main()