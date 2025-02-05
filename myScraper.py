from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_fixed
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import os
import math


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

@dataclass
class PriceHistoryData:
    date: str
    price: str


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
        # "price_history_button": "div.szUogf div.rfmBib"
    }

    PRICESELECTORS = {
        "date": "div.hDLiAd",
        "price": "div.J4Pmnb span"
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

    async def _click_price_graph(self, page) -> None:
        try: 
            # print("trying to click price graph")
            # price_history_button = page.locator("div.VfPpkd-Jh91Gc").first
            price_history_button = await page.wait_for_selector('button[jsname="MinD4b"]', timeout = 30000)
            if price_history_button:
                await price_history_button.click()
                # print("clicked price history graph")
                await page.wait_for_timeout(2000)
        except Exception as e:
            raise Exception(f"Failed to press price history: {str(e)}")


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

    async def _scroll_to_back(self,page) -> None:
        while True:
            try:
                # Wait for the "more flights" button

                back_button = await page.wait_for_selector(
                    'button[aria-label="Scroll backward"]', timeout=5000
                )
                if back_button:
                    await back_button.click()
                    # Wait for new flights to load

                    await page.wait_for_timeout(2000)
                else:
                    break
            except:
                # No more "Show more" button found

                break

    async def _calc_month_value(self, array) -> List[int]:
        try:
            month = array[0]
            if (month == "Jan"):
                return [1,array[1]]
            elif month == "Feb":
                return [2,array[1]]
            elif (month == "Mar"):
                return [3,array[1]]
            elif month == "Apr":
                return [4,array[1]]
            elif (month == "May"):
                return [5,array[1]]
            elif month == "Jun":
                return [6,array[1]]
            elif (month == "Jul"):
                return [7,array[1]]
            elif month == "Aug":
                return [8,array[1]]
            if (month == "Sep"):
                return [9,array[1]]
            elif month == "Oct":
                return [10,array[1]]
            if (month == "Nov"):
                return [11,array[1]]
            elif month == "Dec":
                return [12,array[1]]                
        except Exception as e:
            raise Exception(f"Could not convert month to int: {str(e)}")


    async def _calc_21s(self, date) -> int:
        try:
            splitArray = date.split(",")
            val = splitArray[0]
            mon_day = val.split()
            int_date = await self._calc_month_value(mon_day)
            integer_value = 0
            for i in range(1,int_date[0]):
                if i == 2:
                    integer_value += 31
                elif i == 3:
                    integer_value += 28
                elif i == 4:
                    integer_value += 31
                elif i == 5:
                    integer_value += 30
                elif i == 6:
                    integer_value += 31
                elif i == 7:
                    integer_value += 30
                elif i == 8:
                    integer_value += 31
                elif i == 9:
                    integer_value += 31
                elif i == 10:
                    integer_value += 30
                elif i == 11:
                    integer_value += 31
                elif i == 12:
                    integer_value += 30
            integer_value += int_date[1]-1
            output = math.ceil((365-integer_value)/21)
                                
            # splitArray = [item.strip() for item in date.split(",")]
        except Exception as e:
            raise Exception(f"Could not get 21s: {str(e)}")

    async def _extract_all_points(self,page) -> List[PriceHistoryData]:
        try:
            await self._scroll_to_back(page)
            price_history = []
            # first_rect = await page.query_selector("g.ZMv3u-JNdkSc")
            # print("clicked first rect")
            # await first_rect.click()
            # first_date_element = await page.query_selector(self.PRICESELECTORS["date"])
            # first_date = await self._extract_text(first_date_element)
            # num_presses = await self._calc_21s(first_date)
            day_of_year = datetime.now().timetuple().tm_yday
            # print(day_of_year)
            num_presses = math.ceil((365-day_of_year)/42)
            # if day_of_year + 42*num_presses > 347:
            #     num_presses -= 1
            # price_history.extend(self._extract_price_history_data_points(page))
            final = False
            for i in range(num_presses):
                try:
                    if (i == num_presses-1):
                        final = True
                    # Wait for the "more flights" button

                    forward_button = await page.wait_for_selector(
                        'button[aria-label="Scroll forward"]', timeout=5000
                    )
                    page_prices = await self._extract_price_history_data_points(page, final)
                    price_history.extend(page_prices)
                    if forward_button:
                        await forward_button.click()
                        await forward_button.click()
                        # Wait for new flights to load

                        await page.wait_for_timeout(2000)
                    else:
                        break
                except:
                    # No more "Show more" button found

                    break

            return price_history   
        except Exception as e:
            raise Exception(f"couldn't get through all pages: {str(e)}")
    
    async def _extract_price_history_data_points(self, page, final) -> List[PriceHistoryData]:
        try:
            # await page.wait_for_selector("li.pIav2d", timeout=30000)

            # Load all available flights first

            # await self._load_all_flights(page)

            rects = await page.query_selector_all("g.ZMv3u-JNdkSc")
            price_history = []
            count = 0
            for rect in rects:
                if (count < 42):
                    if not final:
                        count += 1
                    await rect.click()
                    rect_info = {}
                    # rect_info["price"] = 
                    for key,selector in self.PRICESELECTORS.items():
                        element = await page.query_selector(selector)
                        rect_info[key] = await self._extract_text(element)
                    price_history.append(PriceHistoryData(**rect_info))
                else:
                    break
            return price_history
        except Exception as e:
            raise Exception(f"Failed to get price history data: {str(e)}")

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
        # print('Hello')
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
    
    def save_history_results(self, price_history: List[PriceHistoryData], params: SearchParameters) -> str:
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
            "price_history": [vars(price) for price in price_history],
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
                await self._click_price_graph(page)
                # print("clicked price graph")
                # flights = await self._extract_flight_data(page)
                # history = await self._extract_price_history_data_points(page)
                history = await self._extract_all_points(page)
                self.save_history_results(history, params)
                return history
                # self.save_results(flights, params)
                # return flights
            finally:
                await browser.close()


async def main():
    """Main function to demonstrate usage"""
    scraper = FlightScraper()
    params = SearchParameters(
        departure="MIA",
        destination="SEA",
        departure_date="2025-03-01",
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