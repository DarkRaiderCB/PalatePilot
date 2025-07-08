import asyncio
import json
import time
from tools import get_weather, scrape_top_dish_results, scrape_restaurants_for_dish
from julep_client import client

# Create agent
agent = client.agents.create(
    name="PalatePilot",
    about="A simple foodie tour generator",
    model="gpt-4-turbo"
)

agent_id = agent.id


def extract_final_json_from_output(output_list):
    """Extract JSON from Julep execution output"""
    for item in reversed(output_list):
        if item["role"] == "assistant" and item.get("content"):
            text = item["content"]
            try:
                start = text.find("{")
                end = text.rfind("}")
                json_str = text[start:end+1]
                return json.loads(json_str)
            except Exception as e:
                print(f"Could not parse JSON from assistant output: {e}")
                return None
    print("No valid assistant message found.")
    return None


async def generate_foodie_tour(city, weather, dishes, restaurant_infos):
    """Generate foodie tour using Julep with the same structure as final.py"""
    dining_type = "outdoor" if weather["recommendation"] == "outdoor" else "indoor"

    # Format restaurant info for the prompt
    restaurant_context = ""
    for i, (dish, restaurants) in enumerate(zip(dishes, restaurant_infos)):
        restaurant_context += f"\n{dish}: {'; '.join(restaurants[:3])}"

    prompt = f"""
    Create a one-day foodie tour for {city}. Today's weather is {weather['condition']} with a temperature of {weather['temperature']}°C, suitable for {dining_type} dining.
    
    Use these dishes and restaurant information:
    {restaurant_context}
    
    Follow these steps:
    1. Use the three provided dishes as the iconic dishes for {city}.
    2. Select appropriate restaurants from the provided information that serve these dishes.
    3. Generate a narrative for breakfast, lunch, and dinner, including restaurant names, addresses, dish descriptions, and how the weather influences the dining experience.
    4. Output the response as a JSON object with fields: 'city' (string), 'weather' (object with 'temperature' as a number, 'condition' as a string, 'dining' as a string), 'iconic_dishes' (array of three strings), and 'tour' (object with 'breakfast', 'lunch', 'dinner', each containing 'restaurant', 'address', 'dish', 'description', 'weather_consideration' as strings).
    
    Ensure the narrative is engaging, culturally relevant, and reflects the {dining_type} dining environment.
    Return only valid JSON with no extra text, backticks, or markdown formatting.
    """

    try:
        task_definition = {
            "name": "Foodie Tour Generator",
            "description": "Generate a one-day foodie tour for a given city based on weather",
            "main": [
                {
                    "prompt": [
                        {"role": "system",
                            "content": "You are a culinary expert specializing in food tours."},
                        {"role": "user", "content": prompt}
                    ]
                }
            ]
        }

        task = client.tasks.create(agent_id=agent_id, **task_definition)
        execution = client.executions.create(
            task_id=task.id,
            input={
                "city": city,
                "temperature": weather["temperature"],
                "condition": weather["condition"],
                "dining_type": dining_type,
                "dishes": dishes,
                "restaurant_infos": restaurant_infos
            }
        )

        timeout = time.time() + 60
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            time.sleep(2)
            if time.time() > timeout:
                print("Execution timed out after 60 seconds")
                return None

        if result.status == "succeeded":
            return extract_final_json_from_output(result.output)
        else:
            print(f"Execution failed: {result.error}")
            return None

    except Exception as e:
        print(
            f"Error generating foodie tour for {city}: {e.__class__.__name__}: {str(e)}")
        return None


async def run_workflow(city):
    """Main workflow for generating foodie tour"""
    print(f"🌍 Processing {city}...")

    # Get weather data
    print("☀️ Getting weather...")
    weather = await get_weather(city)
    print(f"Weather: {weather}")

    # Get dish information
    print("🍽️ Scraping dish information...")
    dish_text = await scrape_top_dish_results(city)
    if not dish_text:
        print("⚠️ No dish text found, using fallback")
        dishes = ["Traditional Dish 1",
                  "Traditional Dish 2", "Traditional Dish 3"]
    else:
        # Extract dishes using simple parsing (or you can use Julep for this too)
        dishes = await extract_dishes_from_text(city, dish_text)

    print(f"Selected dishes: {dishes}")

    # Get restaurant information
    print("🏪 Getting restaurant information...")
    try:
        restaurant_infos = await asyncio.gather(
            *[scrape_restaurants_for_dish(city, dish) for dish in dishes]
        )
        print(f"Restaurant info gathered for {len(restaurant_infos)} dishes")
    except Exception as e:
        print(f"❌ Error scraping restaurants: {e}")
        restaurant_infos = [[] for _ in dishes]

    # Generate foodie tour
    print("📋 Generating foodie tour...")
    tour_result = await generate_foodie_tour(city, weather, dishes, restaurant_infos)

    if tour_result:
        print(f"\n🎉 Foodie tour for {city}:")
        print("=" * 50)
        print(json.dumps(tour_result, indent=2))
        print("=" * 50)
        return tour_result
    else:
        print(f"❌ Failed to generate foodie tour for {city}")
        return None


async def extract_dishes_from_text(city, dish_text):
    """Extract dishes using Julep (similar to final.py structure)"""
    prompt = f"""
    Extract exactly 3 iconic dishes from the following text about {city}:
    
    {dish_text[:3000]}
    
    Return only a JSON array of 3 dish names, for example: ["Dish 1", "Dish 2", "Dish 3"]
    """

    try:
        task_definition = {
            "name": "Dish Extractor",
            "description": "Extract iconic dishes from text",
            "main": [
                {
                    "prompt": [
                        {"role": "system", "content": "You are a food expert. Extract dish names from text and return only a JSON array."},
                        {"role": "user", "content": prompt}
                    ]
                }
            ]
        }

        task = client.tasks.create(agent_id=agent_id, **task_definition)
        execution = client.executions.create(
            task_id=task.id,
            input={"city": city, "text": dish_text}
        )

        timeout = time.time() + 30
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            time.sleep(2)
            if time.time() > timeout:
                print("Dish extraction timed out")
                return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]

        if result.status == "succeeded":
            # Extract JSON from output
            for item in reversed(result.output):
                if item["role"] == "assistant" and item.get("content"):
                    try:
                        content = item["content"].strip()
                        if content.startswith("```json"):
                            content = content.replace(
                                "```json", "").replace("```", "").strip()
                        elif content.startswith("```"):
                            content = content.replace("```", "").strip()

                        dishes = json.loads(content)
                        if isinstance(dishes, list) and len(dishes) >= 3:
                            return dishes[:3]
                    except:
                        continue

        # Fallback
        return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]

    except Exception as e:
        print(f"Error extracting dishes: {e}")
        return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]


if __name__ == "__main__":
    cities = ["London", "Paris", "Tokyo"]

    async def run_all():
        results = []
        for city in cities:
            print(f"\n🍽️ Generating tour for: {city}")
            print("=" * 60)
            result = await run_workflow(city)
            if result:
                results.append(result)
            print(f"✅ Completed {city}\n")

        # Save results to file
        if results:
            with open("foodie_tours.json", "w") as f:
                json.dump({"foodie_tours": results}, f, indent=2)
            print(f"💾 Saved {len(results)} tours to foodie_tours.json")

    asyncio.run(run_all())
