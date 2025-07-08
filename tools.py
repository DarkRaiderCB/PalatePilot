import aiohttp
from bs4 import BeautifulSoup


async def get_coordinates(city):
    """Get city coordinates using Open-Meteo geocoding API"""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            async with session.get(url, timeout=10) as res:
                data = await res.json()
                if data.get("results"):
                    loc = data["results"][0]
                    return loc["latitude"], loc["longitude"]
        except Exception as e:
            print(f"Error getting coordinates for {city}: {e}")
            return None, None


async def get_weather(city):
    """Get weather data for a city (modified to match final.py structure)"""
    lat, lon = await get_coordinates(city)
    if lat is None:
        return {
            "temperature": 20,
            "condition": "unknown",
            "recommendation": "indoor"
        }

    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&timezone=auto"
            async with session.get(url, timeout=10) as res:
                data = await res.json()
                temp = data["current"]["temperature_2m"]
                code = data["current"]["weather_code"]

                # Map weather codes to conditions
                if code == 0:
                    condition = "clear"
                elif code <= 3:
                    condition = "cloudy"
                elif code <= 67:
                    condition = "rainy"
                else:
                    condition = "stormy"

                # Determine dining recommendation (matching final.py logic)
                is_outdoor = condition == "clear" and temp > 15
                recommendation = "outdoor" if is_outdoor else "indoor"

                return {
                    "temperature": temp,
                    "condition": condition,
                    "recommendation": recommendation
                }
        except Exception as e:
            print(f"Error getting weather for {city}: {e}")
            return {
                "temperature": 20,
                "condition": "unknown",
                "recommendation": "indoor"
            }


async def scrape_top_dish_results(city):
    """Scrape information about top dishes in a city"""
    try:
        from googlesearch import search
    except ImportError:
        print("googlesearch-python not installed. Install with: pip install googlesearch-python")
        return None

    async with aiohttp.ClientSession() as session:
        query = f"famous traditional dishes in {city}"
        snippets = []

        try:
            for url in search(query, num_results=3):
                try:
                    async with session.get(url, timeout=10) as res:
                        text = await res.text()
                        soup = BeautifulSoup(text, "html.parser")

                        # Remove script and style elements
                        for tag in soup(["script", "style"]):
                            tag.decompose()

                        content = soup.get_text(separator=" ").strip()
                        if len(content) > 200:
                            # Limit to 2000 chars
                            snippets.append(content[:2000])

                except Exception as e:
                    print(f"Error scraping {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error in Google search: {e}")

        return "\n\n".join(snippets) if snippets else None


async def scrape_restaurants_for_dish(city, dish):
    """Scrape restaurant information for a specific dish in a city"""
    try:
        from googlesearch import search
    except ImportError:
        print("googlesearch-python not installed. Install with: pip install googlesearch-python")
        return []

    async with aiohttp.ClientSession() as session:
        query = f"best restaurants in {city} serving {dish}"
        results = []

        try:
            for url in search(query, num_results=3):
                try:
                    async with session.get(url, timeout=10) as res:
                        text = await res.text()
                        soup = BeautifulSoup(text, "html.parser")

                        # Remove script and style elements
                        for tag in soup(["script", "style"]):
                            tag.decompose()

                        content = soup.get_text(separator=" ").strip()
                        if len(content) > 200:
                            # Limit to 2000 chars
                            results.append(content[:2000])

                except Exception as e:
                    print(f"Error scraping {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error in Google search for {dish}: {e}")

        return results


# Additional utility functions to match final.py structure
def format_weather_for_prompt(weather):
    """Format weather data for prompt usage"""
    dining_type = "outdoor" if weather["recommendation"] == "outdoor" else "indoor"
    return {
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "dining": dining_type
    }


def format_restaurant_info_for_prompt(dishes, restaurant_infos):
    """Format restaurant information for prompt usage"""
    formatted = []
    for dish, restaurants in zip(dishes, restaurant_infos):
        if restaurants:
            # Extract key information from scraped content
            restaurant_summaries = []
            for restaurant_text in restaurants[:3]:  # Limit to top 3
                # Simple extraction - you can make this more sophisticated
                lines = restaurant_text.split('\n')
                relevant_lines = [line.strip()
                                  for line in lines if len(line.strip()) > 20][:5]
                restaurant_summaries.append(' '.join(relevant_lines))
            formatted.append(f"{dish}: {'; '.join(restaurant_summaries)}")
        else:
            formatted.append(f"{dish}: No specific restaurants found")
    return '\n'.join(formatted)


# Cache for coordinates to avoid repeated API calls
_coordinate_cache = {}


async def get_coordinates_cached(city):
    """Get coordinates with caching"""
    if city in _coordinate_cache:
        return _coordinate_cache[city]

    coords = await get_coordinates(city)
    _coordinate_cache[city] = coords
    return coords
