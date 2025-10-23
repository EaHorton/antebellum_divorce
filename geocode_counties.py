import sqlite3
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

DB_PATH = 'dv_petitions.db'

def get_county_location(county, state):
    """Geocode a county using Nominatim"""
    geolocator = Nominatim(user_agent="antebellum_divorce_project")
    
    # Clean up county name
    county = county.replace('_', ' ')
    
    # Convert state abbreviations to full names
    state_names = {
        'AL': 'Alabama',
        'NC': 'North Carolina',
        'TN': 'Tennessee'
    }
    state_name = state_names.get(state, state)
    
    try:
        # Format the query to specifically look for a county
        query = f"{county} County, {state_name}, USA"
        location = geolocator.geocode(query)
        
        if location:
            return location.latitude, location.longitude
        return None
    except GeocoderTimedOut:
        print(f"Timeout for {county}, {state}")
        return None
    except Exception as e:
        print(f"Error geocoding {county}, {state}: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get all unique county-state combinations
    cur.execute("""
        SELECT DISTINCT county, state
        FROM Petitions
        WHERE county IS NOT NULL AND county != ''
        ORDER BY state, county
    """)
    locations = cur.fetchall()
    
    for county, state in locations:
        # Check if we already have this location
        cur.execute(
            "SELECT 1 FROM Geolocations WHERE county = ? AND state = ?",
            (county, state)
        )
        if cur.fetchone():
            continue
            
        print(f"Geocoding {county}, {state}...")
        coords = get_county_location(county, state)
        
        if coords:
            lat, lon = coords
            cur.execute(
                """
                INSERT INTO Geolocations (county, state, latitude, longitude)
                VALUES (?, ?, ?, ?)
                """,
                (county, state, lat, lon)
            )
            conn.commit()
            print(f"Added {county}, {state} at {lat}, {lon}")
        else:
            print(f"Could not geocode {county}, {state}")
        
        # Be nice to the geocoding service
        time.sleep(1)
    
    conn.close()
    print("Geocoding complete!")

if __name__ == "__main__":
    main()