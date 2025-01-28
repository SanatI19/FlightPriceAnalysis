from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup ChromeDriver with WebDriver Manager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Open Google Flights
driver.get("https://www.google.com/flights")

# Wait for the page to load fully (you can adjust time or use specific elements to wait for)
wait = WebDriverWait(driver, 10)  # Wait for up to 10 seconds

# Wait until the 'From' input field is available and interactable
from_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Where from?']")))
from_input.click()
from_input.send_keys("New York")
from_input.send_keys(Keys.RETURN)

# Wait until the 'To' input field is available and interactable
to_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Where to?']")))
to_input.click()
to_input.send_keys("San Francisco")
to_input.send_keys(Keys.RETURN)

# Allow results to load
time.sleep(5)  # Adjust as needed

# Grab flight data (repeat this process with other elements)
flight_elements = driver.find_elements(By.XPATH, "//li[@class='gws-flights-results__result-item']")
flights = []

for flight in flight_elements:
    try:
        price = flight.find_element(By.XPATH, ".//div[@class='YMlIz']//span").text  # Price
        airline = flight.find_element(By.XPATH, ".//span[@class='gws-flights__ellipses']").text  # Airline
        duration = flight.find_element(By.XPATH, ".//div[@class='gws-flights__duration']").text  # Duration
        flights.append({"Price": price, "Airline": airline, "Duration": duration})
    except Exception as e:
        print(f"Error extracting flight data: {e}")

# Save data to CSV (using Pandas)
import pandas as pd
flight_df = pd.DataFrame(flights)
flight_df.to_csv("google_flights_data.csv", index=False)

# Cleanly quit the browser session
driver.quit()
