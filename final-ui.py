import streamlit as st
import json
import time
import asyncio
from datetime import datetime
from tools import get_weather, scrape_top_dish_results, scrape_restaurants_for_dish
from julep_client import client

# Set page configuration
st.set_page_config(
    page_title="PalatePilot",
    layout="wide",
    page_icon="🍽️"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stApp { max-width: 1200px; margin: auto; }
    .title { font-size: 2.5em; color: #2c3e50; text-align: center; margin-bottom: 0.5em; }
    .subtitle { font-size: 1.2em; color: #7f8c8d; text-align: center; margin-bottom: 2em; }
    .card { background-color: white; padding: 1.5em; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1em; }
    .card-title { font-size: 1.5em; color: #e74c3c; margin-bottom: 0.5em; }
    .card-text { font-size: 1em; color: #34495e; }
    .sidebar .sidebar-content { background-color: #ecf0f1; }
    .stButton>button { background-color: #e74c3c; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #c0392b; }
    .download-section { margin-top: 2em; padding: 1em; background-color: #e8f5e8; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# Initialize agent


@st.cache_resource
def initialize_agent():
    return client.agents.create(
        name="PalatePilot",
        about="A simple PalatePilot tour generator",
        model="gpt-4o"
    )


agent = initialize_agent()
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
                st.warning(f"Could not parse JSON from assistant output: {e}")
                return None
    st.warning("No valid assistant message found.")
    return None


async def generate_tour(city, weather, dishes, restaurant_infos):
    """Generate PalatePilot tour using Julep"""
    dining_type = "outdoor" if weather["recommendation"] == "outdoor" else "indoor"

    # Format restaurant info for the prompt
    restaurant_context = ""
    for i, (dish, restaurants) in enumerate(zip(dishes, restaurant_infos)):
        if restaurants:
            restaurant_context += f"\n{dish}: {'; '.join(restaurants[:2])}"
        else:
            restaurant_context += f"\n{dish}: Popular local restaurants"

    prompt = f"""
    Create a day long PalatePilot tour for {city}. Today's weather is {weather['condition']} with a temperature of {weather['temperature']}°C, suitable for {dining_type} dining.
    
    Use these dishes and restaurant information:
    {restaurant_context}
    
    Follow these steps:
    1. Use the three provided dishes as the iconic dishes for {city}.
    2. Select appropriate restaurants from the provided information that serve these dishes, or suggest well-known establishments.
    3. Generate a narrative for breakfast, lunch, and dinner, including restaurant names, addresses, dish descriptions, and how the weather influences the dining experience.
    4. Output the response as a JSON object with fields: 'city' (string), 'weather' (object with 'temperature' as a number, 'condition' as a string, 'dining' as a string), 'iconic_dishes' (array of three strings), and 'tour' (object with 'breakfast', 'lunch', 'dinner', each containing 'restaurant', 'address', 'dish', 'description', 'weather_consideration' as strings).
    
    Ensure the narrative is engaging, culturally relevant, and reflects the {dining_type} dining environment.
    Return only valid JSON with no extra text, backticks, or markdown formatting.
    """

    try:
        task_definition = {
            "name": "PalatePilot Tour Generator",
            "description": "Generate a one-day PalatePilot tour for a given city based on weather",
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
                "dining_type": dining_type
            }
        )

        timeout = time.time() + 60
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            time.sleep(2)
            if time.time() > timeout:
                st.error("Execution timed out after 60 seconds")
                return None

        if result.status == "succeeded":
            return extract_final_json_from_output(result.output)
        else:
            st.error(f"Execution failed: {result.error}")
            return None

    except Exception as e:
        st.error(
            f"Error generating PalatePilot tour for {city}: {e.__class__.__name__}: {str(e)}")
        return None


async def extract_dishes_from_text(city, dish_text):
    """Extract dishes using Julep"""
    if not dish_text:
        return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]

    prompt = f"""
    Extract exactly 3 iconic dishes from the following text about {city}:
    
    {dish_text[:2000]}
    
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
                return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]

        if result.status == "succeeded":
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

        return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]

    except Exception as e:
        st.error(f"Error extracting dishes: {e}")
        return ["Traditional Dish 1", "Traditional Dish 2", "Traditional Dish 3"]


async def process_city(city):
    """Process a single city to generate PalatePilot tour"""
    # Get weather data
    weather = await get_weather(city)

    # Get dish information
    dish_text = await scrape_top_dish_results(city)
    dishes = await extract_dishes_from_text(city, dish_text)

    # Get restaurant information
    try:
        restaurant_infos = await asyncio.gather(
            *[scrape_restaurants_for_dish(city, dish) for dish in dishes]
        )
    except Exception as e:
        st.warning(f"Error scraping restaurants for {city}: {e}")
        restaurant_infos = [[] for _ in dishes]

    # Generate PalatePilot tour
    tour_result = await generate_tour(city, weather, dishes, restaurant_infos)
    return tour_result


def create_markdown_content(tours):
    """Create markdown content from tour results"""
    markdown_content = f"""# PalatePilot Tour Guide
*Generated on {datetime.now().strftime('%B %d, %Y')}*

---

"""

    for tour in tours:
        city = tour["city"]
        weather = tour["weather"]
        dishes = tour["iconic_dishes"]

        markdown_content += f"""## {city} PalatePilot Tour

### Weather Information
- **Temperature**: {weather['temperature']}°C
- **Condition**: {weather['condition'].capitalize()}
- **Dining Recommendation**: {weather['dining'].capitalize()}

### Iconic Dishes
{', '.join(f"**{dish}**" for dish in dishes)}

### Daily Itinerary

"""

        for meal_type in ["breakfast", "lunch", "dinner"]:
            meal = tour["tour"][meal_type]
            markdown_content += f"""#### {meal_type.capitalize()}

**Restaurant**: {meal['restaurant']}  
**Address**: {meal['address']}  
**Dish**: {meal['dish']}  

**Description**: {meal['description']}

**Weather Consideration**: {meal['weather_consideration']}

---

"""

    return markdown_content


def create_text_content(tours):
    """Create plain text content from tour results"""
    lines = [
        f"PalatePilot Tour Guide\nGenerated on {datetime.now().strftime('%B %d, %Y')}\n\n"]
    for tour in tours:
        city = tour["city"]
        weather = tour["weather"]
        dishes = tour["iconic_dishes"]
        lines.append(f"City: {city}")
        lines.append(
            f"  Weather: {weather['condition'].capitalize()}, {weather['temperature']}°C, {weather['dining'].capitalize()} dining")
        lines.append(f"  Iconic Dishes: {', '.join(dishes)}")
        lines.append(f"  Daily Itinerary:")
        for meal_type in ["breakfast", "lunch", "dinner"]:
            meal = tour["tour"][meal_type]
            lines.append(f"    {meal_type.capitalize()}:")
            lines.append(f"      Restaurant: {meal['restaurant']}")
            lines.append(f"      Address: {meal['address']}")
            lines.append(f"      Dish: {meal['dish']}")
            lines.append(f"      Description: {meal['description']}")
            lines.append(
                f"      Weather Consideration: {meal['weather_consideration']}")
        lines.append("")
    return '\n'.join(lines)


# Main Streamlit UI
st.markdown('<div class="title">PalatePilot Food Tour Generator 🍽️</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Plan your culinary adventure with weather-based dining recommendations!</div>', unsafe_allow_html=True)

# Sidebar for city selection
with st.sidebar:
    st.header("City Selection")

    # Allow user to enter multiple cities by typing (comma-separated)
    city_input = st.text_input(
        "Enter cities (comma-separated):",
        placeholder="e.g. Paris, New York, Tokyo",
        help="Type one or more cities separated by commas."
    )
    selected_cities = []
    if city_input:
        selected_cities = [c.strip()
                           for c in city_input.split(',') if c.strip()]

    # Custom city input (no longer needed, so removed)

    # Display selected cities
    if selected_cities:
        st.markdown(f"**Selected cities:** {', '.join(selected_cities)}")
    else:
        st.warning("Please enter at least one city.")

    # Options
    st.header("Options")
    include_weather = st.checkbox(
        "Include detailed weather analysis", value=True)
    include_raw_json = st.checkbox("Show raw JSON data", value=False)

# Main content area
st.info("🌍 Enter any city worldwide to generate a personalized PalatePilot tour based on current weather conditions!")

# Generate tours button
if st.button("🍽️ Generate PalatePilot Tours", disabled=not selected_cities):
    if selected_cities:
        # Initialize session state for results
        if 'tour_results' not in st.session_state:
            st.session_state.tour_results = []

        st.session_state.tour_results = []

        # Process each city
        for city in selected_cities:
            with st.spinner(f"🔄 Processing {city}..."):
                try:
                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(process_city(city))
                    loop.close()

                    if result:
                        st.session_state.tour_results.append(result)
                        st.success(f"✅ PalatePilot tour generated for {city}")
                    else:
                        st.error(
                            f"❌ Failed to generate PalatePilot tour for {city}")

                except Exception as e:
                    st.error(f"❌ Error processing {city}: {str(e)}")

                # Small delay between cities
                time.sleep(1)

# Display results
if 'tour_results' in st.session_state and st.session_state.tour_results:
    st.subheader("🎉 PalatePilot Tour Results")

    # Display each tour
    for tour in st.session_state.tour_results:
        city = tour["city"]

        with st.expander(f"🍽️ PalatePilot Tour for {city}", expanded=True):
            # Weather information
            weather = tour['weather']
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Temperature", f"{weather['temperature']}°C")
            with col2:
                st.metric("Condition", weather['condition'].capitalize())
            with col3:
                st.metric("Dining Style", weather['dining'].capitalize())

            # Iconic dishes
            st.markdown("### 🥘 Iconic Dishes")
            st.markdown(f"**{', '.join(tour['iconic_dishes'])}**")

            # Daily itinerary
            st.markdown("### 📅 Daily Itinerary")

            for meal_type in ["breakfast", "lunch", "dinner"]:
                meal = tour["tour"][meal_type]

                # Meal header with icon
                meal_icons = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}
                st.markdown(
                    f"#### {meal_icons[meal_type]} {meal_type.capitalize()}")

                # Meal details in columns
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**🏪 Restaurant**: {meal['restaurant']}")
                    st.markdown(f"**📍 Address**: {meal['address']}")
                    st.markdown(f"**🍽️ Dish**: {meal['dish']}")
                    st.markdown(f"**📖 Description**: {meal['description']}")

                with col2:
                    st.markdown(
                        f"**🌤️ Weather Consideration**: {meal['weather_consideration']}")

                st.markdown("---")

            # Raw JSON (if enabled)
            if include_raw_json:
                st.markdown("### 📋 Raw JSON Data")
                st.json(tour)

    # Download section
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("### 📥 Download Options")

    col1, col2 = st.columns(2)

    with col1:
        # JSON download
        json_str = json.dumps(
            {"PalatePilot_tours": st.session_state.tour_results}, indent=2)
        st.download_button(
            label="📄 Download as JSON",
            data=json_str,
            file_name=f"PalatePilot_tours_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    with col2:
        # Text file download
        text_content = create_text_content(st.session_state.tour_results)
        st.download_button(
            label="📝 Download as Text",
            data=text_content,
            file_name=f"PalatePilot_tours_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d;">
    <p>🚀 Powered by Julep API, Open-Meteo Weather API, Google Search, and Streamlit</p>
    <p>Made with ❤️ for food lovers around the world</p>
</div>
""", unsafe_allow_html=True)
