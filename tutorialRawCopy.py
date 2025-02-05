from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_fixed
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import os


@dataclass
class SearchParameters:
    """Data class to store flight search parameters"""

    departure: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    ticket_type: str = "One way"


@dataclass
class FlightData:
    """Data class to store individual flight information"""

    airline: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: str
    price: str
    co2_emissions: str
    emissions_variation: str


class FlightScraper:
    """Class to handle Google Flights scraping operations"""

    SELECTORS = {
        "airline": "div.sSHqwe.tPgKwe.ogfYpf",
        "departure_time": 'span[aria-label^="Departure time"]',
        "arrival_time": 'span[aria-label^="Arrival time"]',
        "duration": 'div[aria-label^="Total duration"]',
        "stops": "div.hF6lYb span.rGRiKd",
        "price": "div.FpEdX span",
        "co2_emissions": "div.O7CXue",
        "emissions_variation": "div.N6PNV",
    }

    def __init__(self):
        self.results_dir = "flight_results"
        os.makedirs(self.results_dir, exist_ok=True)

    async def _extract_text(self, element) -> str:
        """Extract text content from a page element safely"""
        if element:
            return (await element.text_content()).strip()
        return "N/A"

    async def _load_all_flights(self, page) -> None:
        """Click 'Show more flights' button until all flights are loaded"""
        while True:
            try:
                # Wait for the "more flights" button

                more_button = await page.wait_for_selector(
                    'button[aria-label*="more flights"]', timeout=5000
                )
                if more_button:
                    await more_button.click()
                    # Wait for new flights to load

                    await page.wait_for_timeout(2000)
                else:
                    break
            except:
                # No more "Show more" button found

                break

    async def _extract_flight_data(self, page) -> List[FlightData]:
        """Extract flight information from search results"""
        try:
            await page.wait_for_selector("li.pIav2d", timeout=30000)

            # Load all available flights first

            await self._load_all_flights(page)

            # Now extract all flight data

            flights = await page.query_selector_all("li.pIav2d")

            flights_data = []
            for flight in flights:
                flight_info = {}
                for key, selector in self.SELECTORS.items():
                    element = await flight.query_selector(selector)
                    flight_info[key] = await self._extract_text(element)
                flights_data.append(FlightData(**flight_info))
            return flights_data
        except Exception as e:
            raise Exception(f"Failed to extract flight data: {str(e)}")

    async def _fill_search_form(self, page, params: SearchParameters) -> None:
        """Fill out the flight search form"""
        # Select ticket type

        ticket_type_div = page.locator("div.VfPpkd-TkwUic[jsname='oYxtQd']").first
        await ticket_type_div.click()
        await page.wait_for_selector("ul[aria-label='Select your ticket type.']")
        await page.locator("li").filter(has_text=params.ticket_type).nth(0).click()
        await page.wait_for_timeout(1000)

        # Fill departure location

        from_input = page.locator("input[aria-label='Where from?']")
        await from_input.click()
        await from_input.fill("")
        await page.wait_for_timeout(500)
        await page.keyboard.type(params.departure)
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(1000)

        # Fill destination

        await page.keyboard.type(params.destination)
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(4000)

        # Fill dates

        await page.keyboard.type(params.departure_date)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(1000)

        if params.ticket_type == "Round trip" and params.return_date:
            await page.keyboard.type(params.return_date)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(1000)
        else:
            await page.keyboard.press("Tab")
        # print('Skipped round trip')
        await page.keyboard.press("Enter")
        # print('Pressed enter')
        await page.wait_for_timeout(8000)

    def save_results(self, flights: List[FlightData], params: SearchParameters) -> str:
        """Save flight search results to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flight_results_{params.departure}_{params.destination}_{timestamp}.json"

        output_data = {
            "search_parameters": {
                "departure": params.departure,
                "destination": params.destination,
                "departure_date": params.departure_date,
                "return_date": params.return_date,
                "search_timestamp": timestamp,
            },
            "flights": [vars(flight) for flight in flights],
        }

        filepath = os.path.join(self.results_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        return filepath

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def search_flights(self, params: SearchParameters) -> List[FlightData]:
        """Execute the flight search with retry capability"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto("https://www.google.com/flights", timeout=60000)
                await self._fill_search_form(page, params)
                flights = await self._extract_flight_data(page)
                self.save_results(flights, params)
                return flights
            finally:
                await browser.close()


async def main():
    """Main function to demonstrate usage"""
    scraper = FlightScraper()
    params = SearchParameters(
        departure="MIA",
        destination="SEA",
        departure_date="2024-12-01",
        # return_date="2024-12-30",
        ticket_type="One way",
    )

    try:
        flights = await scraper.search_flights(params)
        print(f"Successfully found {len(flights)} flights")
    except Exception as e:
        print(f"Error during flight search: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())