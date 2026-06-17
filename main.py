import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
import os 

# --- CONFIGURATION ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 

TARGET_COMPANY = "Google"          # Your desired company
TARGET_UNIVERSITY = "Stanford University" # Your university name
MAX_REQUESTS_PER_RUN = 10          # CRITICAL SAFETY LIMIT: Start small (5-10) and only run once per day.

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# --- 1. SETUP: BROWSER INITIALIZATION (NO LOGIN) ---
def setup_browser():
    """Initializes the Chrome browser, assuming user is already logged in."""
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment to run without a visible browser window
    
    # Use a persistent user data directory if you want to ensure the session/login sticks.
    # Replace 'C:\\...\\LinkedIn_Profile' with a custom path on your machine.
    # options.add_argument("user-data-dir=/path/to/your/chrome/profile") 
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Navigate to LinkedIn to ensure the session is active
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(random.uniform(2, 4))
    
    if "login" in driver.current_url.lower():
        print("ERROR: Login check failed. Please ensure you are logged in before running this script.")
        driver.quit()
        raise Exception("Not Logged In")
        
    print("Browser setup complete. LinkedIn session appears active.")
    return driver

# --- 2. SEARCH & SCRAPE PROFILES ---
def search_and_get_profiles(driver, company, university):
    """Navigates to the search URL with filters and scrapes profile links."""
    
    # Constructing a clean search URL based on People, Current Company, and School filters.
    # NOTE: This format is based on typical LinkedIn URLs but may break if LinkedIn updates its structure.
    search_url = (
        f"https://www.linkedin.com/search/results/people/"
        f"?currentCompany={company.replace(' ', '%20')}"
        f"&school={university.replace(' ', '%20')}"
        f"&origin=SWITCH_SEARCH_VERTICAL"
    )

    print(f"Navigating to search results for {company} employees from {university}...")
    driver.get(search_url)
    time.sleep(random.uniform(5, 7))

    # XPATH to locate profile elements on the search results page.
    # This targets the main link element for a profile.
    profile_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/in/') and not(contains(@href, '/public-profile/'))]")
    
    profile_data = []
    unique_urls = set()

    for element in profile_elements:
        url = element.get_attribute('href').split('?')[0]
        # Basic filter to ensure it's a person's profile
        if "/in/" in url and url not in unique_urls:
            try:
                # Attempt to find the person's name element within the profile card
                name_element = element.find_element(By.XPATH, ".//span[@aria-hidden='true']")
                name = name_element.text if name_element else "Unknown Name"
                
                profile_data.append({'url': url, 'name': name})
                unique_urls.add(url)
                
                if len(profile_data) >= MAX_REQUESTS_PER_RUN:
                    break
            except Exception:
                # Skip if the name element couldn't be found (e.g., non-person link)
                continue

    print(f"Found {len(profile_data)} unique profiles to process.")
    return profile_data

# --- 3. AI MESSAGE GENERATION ---
def generate_coffee_chat_note(name, company, university):
    """Calls the OpenAI API to generate a personalized connection note."""
    print(f"Generating note for {name}...")
    
    # Prompting for a professional, concise, and friendly note
    prompt = (
        f"Write a short, professional, and friendly LinkedIn connection request note (MAX 250 characters) "
        f"to {name}, who works at {company}. The sender is an alumnus/student from {university}. "
        f"The purpose is to request a brief virtual coffee chat to learn about their career path. "
        f"Start with 'Hi [First Name],'"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional networking assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=80 # Keep tokens low to ensure message brevity
        )
        
        # Extract and clean up the message
        note = response.choices[0].message.content.strip().replace('\n', ' ')
        
        # Replace the placeholder [First Name] with the actual name
        first_name = name.split()[0]
        note = note.replace("Hi [First Name],", f"Hi {first_name},")
        
        # Ensure it fits the 300 character limit for LinkedIn notes
        return note[:300]
    
    except Exception as e:
        print(f"OpenAI API call failed: {e}. Using fallback message.")
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
    if not OPENAI_API_KEY:
        print("FATAL ERROR: Please set your OPENAI_API_KEY environment variable.")
        return

    driver = setup_browser()
    
    try:
        # 1. Get the list of profiles
        profiles = search_and_get_profiles(driver, TARGET_COMPANY, TARGET_UNIVERSITY)
        
        # 2. Iterate and send requests
        for profile in profiles:
            name = profile['name']
            url = profile['url']
            
            # Generate personalized note
            note = generate_coffee_chat_note(name, TARGET_COMPANY, TARGET_UNIVERSITY)
            
            # Send the connection request
            send_connection_request(driver, url, name, note)
            
            # CRITICAL: Add a randomized delay to avoid LinkedIn detection
            delay = random.uniform(45, 120) # Delay between 45 and 120 seconds (1.5 - 2 minutes)
            print(f"Pausing for {round(delay, 2)} seconds before processing the next profile...")
            time.sleep(delay)

    finally:
        print("Automation finished. Closing browser.")
        driver.quit()

if __name__ == "__main__":
    main()