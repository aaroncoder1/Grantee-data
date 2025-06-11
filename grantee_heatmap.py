import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import folium
from folium.plugins import HeatMap
import pandas as pd
import time

# --- 1. Web Scraping: Extract Grantee Locations ---
print("Step 1: Scraping grantee locations from xrplgrants.org...")

GRANTEES_URL = "https://xrplgrants.org/grantees"
locations = []

try:
    response = requests.get(GRANTEES_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    grantee_cards = soup.find_all('div', class_='card-grantee') 



    if not grantee_cards:
        print("Warning: No grantee cards found with the primary selector. The website's HTML might have changed significantly.")

    print(f"Found {len(grantee_cards)} potential grantee cards.")

    for card in grantee_cards:

    # Step 1: Find the <div class="icon-location"> itself
        icon_div = card.find('div', class_='icon-location')

        if icon_div:
        # Step 2: Get its next sibling (which is the text node like "Brazil")
            location_text_node = icon_div.next_sibling

            if location_text_node:
                location_text = str(location_text_node).strip()
                if location_text:
                    locations.append(location_text)


    print(f"Scraped {len(locations)} potential locations.")
    print("Example locations:", locations[:5])

except requests.exceptions.RequestException as e:
    print(f"Error fetching URL: {e}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred during scraping: {e}")
    exit()

if not locations:
    print("No locations were scraped. Cannot proceed with heatmap. Please check the website structure or the scraper code.")
    exit()


# --- 2. Geocoding Locations ---
print("\nStep 2: Geocoding locations...")

geolocator = Nominatim(user_agent="xrpl-grantee-heatmap-analyzer")
# Rate limiter
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5, max_retries=3, error_wait_seconds=5)

geocoded_locations = []
unique_locations = list(set(locations)) # Get unique locations to minimize geocoding requests

for i, loc_name in enumerate(unique_locations):
    print(f"  Geocoding '{loc_name}' ({i+1}/{len(unique_locations)})...")
    try:
        location = geocode(loc_name, timeout=10) # Add a timeout for geocoding
        if location:
            geocoded_locations.append({
                'name': loc_name,
                'latitude': location.latitude,
                'longitude': location.longitude
            })
        else:
            print(f"    Could not geocode '{loc_name}'.")
    except Exception as e:
        print(f"    Error geocoding '{loc_name}': {e}")
    time.sleep(0.5) # Small delay between geocoding requests

print(f"Successfully geocoded {len(geocoded_locations)} unique locations.")

if not geocoded_locations:
    print("No locations were successfully geocoded. Cannot create heatmap.")
    exit()

# Convert to DataFrame for easier manipulation
df_locations = pd.DataFrame(geocoded_locations)

# --- 3. Aggregate Data for Heatmap ---
print("\nStep 3: Aggregating data for heatmap...")
# Count occurrences of each geocoded location
location_counts = df_locations.groupby(['latitude', 'longitude']).size().reset_index(name='count')

# Prepare data for HeatMap plugin: list of [latitude, longitude, count]
heat_data = [[row['latitude'], row['longitude'], row['count']] for index, row in location_counts.iterrows()]

print(f"Prepared {len(heat_data)} data points for heatmap.")

# --- 4. Create Heatmap Visualization ---
print("\nStep 4: Creating heatmap visualization...")

# Create a base map centered roughly in the middle of the world, or first geocoded point
map_center_lat = location_counts['latitude'].mean() if not location_counts.empty else 0
map_center_lon = location_counts['longitude'].mean() if not location_counts.empty else 0

m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=2)

# Add the HeatMap layer
HeatMap(heat_data).add_to(m)

# Save the map to an HTML file
output_html_file = "xrpl_grantees_heatmap.html"
m.save(output_html_file)

print(f"\nHeatmap generated successfully! Open '{output_html_file}' in your web browser to view it.")
print("Analysis complete.")