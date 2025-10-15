import sqlite3
import random
import re
import tkinter as tk
from tkinter import colorchooser
import customtkinter as ctk
import tkintermapview
import threading
import time
from PIL import Image
from os import path
import requests
from geopy.geocoders import Nominatim
from datetime import date, datetime, timedelta
import calendar
import math
from typing import List, Dict, Tuple, Optional

#Global theme Configuration
main_colour_theme="#00199c"

class Outerinator(ctk.CTk):
    #Main application class for Outerinator - an outing planning application.
    #Handles the main window and frame management for the entire application.
    
    def __init__(self):
        #Initialise the main application window and set up all frames.
        #Configures the container system for seamless frame switching.
        super().__init__()
        
        #Configure main window properties
        self.title("Outerinator")
        self.geometry("1000x600")
        
        #Track the logged-in user
        self.current_user_id = None
        self.current_username = None
        
        #Creating database connection and ensuring tables exist
        with sqlite3.connect("outerinator.db") as conn:
            cursor = conn.cursor()
            
            #Create users table with id primary key
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    theme TEXT DEFAULT 'dark',
                    main_colour TEXT DEFAULT '#00ffd9'
                )
            """)
            
            #Create plans table with user_id foreign key
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_name TEXT,
                    start_location TEXT,
                    date TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
        
        #Create a container frame to hold all application frames
        #This allows for smooth transitions between different views
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        #Dictionary to store all frame instances for quick access
        self.frames = {}
        
        #Dynamically create instances of each frame class
        #This ensures all frames are initialised and ready for display
        frame_classes = (OpeningFrame, SigninFrame, SignUpFrame, MainPageFrame, PlanningFrame)
        for FrameClass in frame_classes:
            frame_name = FrameClass.__name__
            frame = FrameClass(parent=container, controller=self)
            self.frames[frame_name] = frame
            #All frames occupy the same grid position, only one visible at a time
            frame.grid(row=0, column=0, sticky="nsew")
        
        #Display the initial frame when application starts
        self.show_frame("OpeningFrame")
    
    def show_frame(self, frame_name: str) -> None:
        #Switch between different application frames.
        #Args: frame_name (str): The name of the frame class to display
        
        frame = self.frames[frame_name]
        #Bring the specified frame to the front of the stacking order
        frame.tkraise()

    def apply_theme(self, theme: str) -> None:
    #Apply and save theme preference
        self.current_theme = theme
        ctk.set_appearance_mode(theme)
    
        if self.current_user_id:
            try:
                with sqlite3.connect("outerinator.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, self.controller.current_user_id))
                    conn.commit()
            except Exception:
                pass
            
    def apply_main_colour(self, colour_hex: str):
        #Apply the main colour theme dynamically across all frames.
        self.main_colour_theme = colour_hex
        for name, frame in self.frames.items():
            if hasattr(frame, "configure"):
                try:
                    frame.configure(fg_color=colour_hex)
                except Exception as e:
                    raise RuntimeError(f"Failed to apply main colour to frame '{name}': {e}") from e
            
    def save_main_colour_preference(self, colour_hex: str) -> None:
        #Save the user's preferred main colour to the database.
        if not getattr(self, "current_user_id", None):
            return
        try:
            with sqlite3.connect("outerinator.db", timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                cols = [row[1] for row in cursor.fetchall()]
                if "main_colour" not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN main_colour TEXT DEFAULT NULL")
                    conn.commit()

                cursor.execute(
                    "UPDATE users SET main_colour = ? WHERE id = ?",
                    (colour_hex, self.current_user_id)
                )   
                conn.commit()
        except sqlite3.Error:
            return


class MapWidget(ctk.CTkFrame):
    #Custom map widget that integrates OpenStreetMap functionality
    #with search, geocoding, and marker management features.    
    def setup_geocoder(self) -> None:
        #Initialise the geocoder service for address lookup and coordinate conversion.
        try:
            #Initialise Nominatim geocoder with custom user agent
            #User agent is required by OpenStreetMap's usage policy
            self.geolocator = Nominatim(user_agent="outerinator_app/1.0 (your_email@example.com)")
        except Exception:
            #Handle geocoder initialisation failure
            self.geolocator = None

    def setup_map(self, width: int, height: int) -> None:
        #Initialise the interactive map component.
        
        #Args: width (int): Map display width, height (int): Map display height
        
        try:
            #Create the main map widget using tkintermapview
            self.map_widget = tkintermapview.TkinterMapView(self, width=width, height=height, corner_radius=8)
            self.map_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            
            #Set initial map position to Auckland
            self.map_widget.set_position(-36.8509, 174.7645)
            self.map_widget.set_zoom(12)
            
            #Configure the tile server for map imagery
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
            
            #Add an initial marker at Auckland city center
            self.map_widget.set_marker(-36.8509, 174.7645, text="Auckland City")
            
        except Exception as e:
            #Display error message if map fails to load
            error_label = ctk.CTkLabel(self, text=f"Map failed to load: {str(e)}", text_color="red", font=("Arial", 10))
            error_label.grid(row=0, column=0)

    def setup_map_controls(self) -> None:
        #Set up the control panel with search and map interaction buttons.
        #Create frame for map controls
        controls_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        controls_frame.grid_propagate(False)  #Maintain fixed height
        controls_frame.columnconfigure(0, weight=1)  #Allow controls to expand
        
        #Search controls section (left-aligned)
        search_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="w")
        
        #Search input field
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search...", width=120, height=25)
        self.search_entry.pack(side="left", padx=(0, 3))
        
        #Search button with magnifying glass icon to signify searching as it is a easily recgnisable sign
        self.search_btn = ctk.CTkButton(search_frame, text="🔍", command=self.robust_search_location, width=30, height=25)
        self.search_btn.pack(side="left", padx=(0, 5))
        
        #Clear results button
        clear_results_btn = ctk.CTkButton(search_frame, text="❌", command=self.clear_address_results, width=25, height=25, fg_color="transparent", hover_color="#333333")
        clear_results_btn.pack(side="left", padx=(0, 5))
        
        #Action buttons section (right-aligned)
        action_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")
        
        #Add marker button
        add_marker_btn = ctk.CTkButton(action_frame, text="📍", command=self.add_marker_at_center, width=30, height=25)
        add_marker_btn.pack(side="left", padx=2)
        
        #Clear all markers button
        clear_markers_btn = ctk.CTkButton(action_frame, text="🗑️", command=self.clear_all_markers, width=30, height=25)
        clear_markers_btn.pack(side="left", padx=2)
        
        #Error display label for map operations
        self.map_error_label = ctk.CTkLabel(action_frame, text="", text_color="red", font=("Arial", 10))
        self.map_error_label.pack(side="left", padx=5)
    
    def robust_search_location(self) -> None:      
        #Perform location search using custom implementation to bypass 
        #tkintermapview's built-in search limitations.
        #Uses threading to prevent UI freezing during search operations.
        query = self.search_entry.get().strip()
        if not query:
            return  #Ignore empty search queries
        
        #Update button to show search in progress
        self.search_btn.configure(state="disabled", text="Searching...")
        
        #Clear any previous search results
        self.clear_address_results()
        
        #Execute search in separate thread to maintain UI responsiveness
        search_thread = threading.Thread(target=self.search_thread_target, args=(query,), daemon=True)
        search_thread.start()
        
    def search_thread_target(self, query: str) -> None:
    #Target function for search thread execution.
    #Args: query (str): The search query string
    
        try:
            #Rate limiting: wait before making API request to avoid 403 errors
            time.sleep(1)

            #Fetch all location results matching the query
            results = self.get_all_locations(query)
        
            #Update UI in the main thread based on search results
            if results:
                self.show_address_results(results)
            else:
                self.on_search_error()
            
        except Exception as e:
            error_msg = str(e)
            msg=error_msg 
            self.on_search_error(msg)
        
    def get_all_locations(self, query: str) -> Optional[List[Dict]]:
        #Query OpenStreetMap Nominatim API for location data.
        #Args: query (str): Location search query
            
        #Returns: Optional[List[Dict]]: List of location results or None if error

        #Configure HTTP headers for API request
        headers = {'User-Agent': 'OuterinatorApp/1.0 (https://myapp.com)', 'Accept': 'application/json', 'Referer': 'https://myapp.com'}
    
        try:
            #Make API request to OpenStreetMap Nominatim service
            response = requests.get(
                "https://nominatim.openstreetmap.org/search", params={'q': query, 'format': 'json', 'addressdetails': 1}, headers=headers,timeout=10 )
        
            if response.status_code == 200:
                data = response.json()
                return data if data else None
            else:
                #Display API error status
                self.map_error_label.configure(text=f"API returned status: {response.status_code}")
                self.clear_error_after_delay()
                return None
            
        except Exception as e:
            #Display network or request error
            self.map_error_label.configure(text=f"Search error: {e}")
            self.clear_error_after_delay()
            return None
        
    def clear_error_after_delay(self) -> None:
        #Clear error messages after a 3 second delay.
        self.after(3000, lambda: self.map_error_label.configure(text=""))
        
    def show_address_results(self, results: List[Dict]) -> None:
        #Display search results in a scrollable frame with clickable items.
        
        #Args: results (List[Dict]): List of location results from search
        
        #Reset search button to normal state
        self.search_btn.configure(state="normal", text="Search")
    
        #Create scrollable results frame if it doesn't exist
        if not hasattr(self, 'results_frame'):
            self.results_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=6)
            self.results_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
            
            #Grid configure
            self.results_frame.grid_rowconfigure(0, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)

            #Create scrollable container inside results frame
            self.scrollable_frame = ctk.CTkScrollableFrame(self.results_frame, fg_color="#1a1a1a", height=150)
            self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
    
        #Ensure results frame is visible
        self.results_frame.grid()
    
        #Clear any previous results from scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
        #Display results count header
        results_count = len(results)
        title_text = f"Found {results_count} locations (showing all):"
    
        title_label = ctk.CTkLabel(self.scrollable_frame, text=title_text, font=("Arial", 12, "bold"), text_color="white")
        title_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 10))
    
        #Create clickable button for each search result
        for i, result in enumerate(results):
            display_name = self.format_display_name(result)
            country = result.get('display_name', '').split(',')[-1].strip()

            #Create a frame to hold each result neatly
            result_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#2a2a2a", corner_radius=4)
            result_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=4)
            result_frame.grid_columnconfigure(0, weight=1)

            #Result button (main line)
            result_btn = ctk.CTkButton(result_frame, text=display_name, command=lambda r=result: self.select_address(r), fg_color="#2a2a2a", hover_color="#3a3a3a", text_color="white", anchor="w", height=28)
            result_btn.grid(row=0, column=0, sticky="ew")

            #Smaller label below for country
            country_label = ctk.CTkLabel(result_frame, text=country, font=("Arial", 9), text_color="#aaaaaa")
            country_label.grid(row=1, column=0, sticky="w", padx=(10, 0))

        
    def format_display_name(self, result: Dict) -> str:
        #Format a readable display name from the raw result data.
        #Truncates very long addresses while maintaining key information.
        
        #Args: result (Dict): Raw location data from search
            
        #Returns: str: Formatted display name
        address = result.get('display_name', 'Unknown Location')
        
        #Handle very long address strings by truncating intelligently
        if len(address) > 80:
            parts = address.split(',')
            if len(parts) >= 4:
                #Show first 4 address components for context
                address = ', '.join(parts[:4])
            else:
                #Simple truncation for addresses with fewer components
                address = address[:80] + "..."
        
        return address
        
    def select_address(self, result: Dict) -> None:
    #Handle address selection from search results.
    #Updates map position and adds marker for selected location.
    
    #Args: result (Dict): Selected location data
    
        #Extract coordinates from result
        lat = float(result['lat'])
        lon = float(result['lon'])
        display_name = self.format_display_name(result)
    
        #Update map to show selected location
        self.update_map_position(lat, lon, display_name)
    
        #Zoom in closely on selected location
        self.map_widget.set_zoom(20)
    
        #Clear the results display after selection
        self.clear_address_results()

        #Notify parent if callback is registered
        if hasattr(self, 'location_callback') and self.location_callback:
            self.location_callback(lat, lon, display_name)
        
    def set_location_callback(self, callback) -> None:
    #Set callback function to be called when location is selected
    
    #Args: callback: Function to call with (lat, lon, name) when location selected
    
        self.location_callback = callback
        
    def clear_address_results(self) -> None:
        #Clear the address search results display.
        if hasattr(self, 'results_frame'):
            if hasattr(self, 'scrollable_frame'):
                #Remove all result widgets from scrollable frame
                for widget in self.scrollable_frame.winfo_children():
                    widget.destroy()
            #Hide the results frame
            self.results_frame.grid_forget()
        
    def update_map_position(self, lat: float, lon: float, query: str) -> None:
        
        #Update map to show specified coordinates and add marker.
        
        #Args: lat (float): Latitude coordinate, lon (float): Longitude coordinate, query (str): Location name for marker
        try:
            #Center map on specified coordinates
            self.map_widget.set_position(lat, lon)

            #Add marker at the location
            self.map_widget.set_marker(lat, lon, text=query)

            #Clear the search entry field
            self.search_entry.delete(0, "end")
        
        except Exception as e:
            #Handle map update errors
            self.map_error_label.configure(text=f"Map update error: {e}")
            self.clear_error_after_delay() 
        
    def on_search_success(self) -> None:
        #Handle successful search completion.
        self.search_btn.configure(state="normal", text="Search")
        self.search_entry.delete(0, "end")
        
    def on_search_error(self, error_msg: str = "") -> None:
        #Handle search failure and display error message.
        
        #Args: error_msg (str): Optional custom error message
        self.search_btn.configure(state="normal", text="Search")
        
        #Use custom error message or default
        error_text = error_msg if error_msg else "Search error: Location not found"
        self.map_error_label.configure(text=error_text)
    
        #Clear error after delay
        self.clear_error_after_delay()
    
        #Display error in results frame
        if not hasattr(self, 'results_frame'):
            self.results_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=6)
            self.results_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
            
            #Results frame grid configuration
            self.results_frame.grid_rowconfigure(0, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)
        
            self.scrollable_frame = ctk.CTkScrollableFrame(self.results_frame, fg_color="#1a1a1a", height=150)
            self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
        #Clear previous content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        #Display error message
        error_label = ctk.CTkLabel(self.scrollable_frame, text="No locations found. Try a more specific search.", text_color="#ff6b6b", font=("Arial", 11))
        error_label.pack(pady=10)
        
    def add_marker_at_center(self) -> None:
        #Add a marker at the current center of the map view.
        position = self.map_widget.get_position()
        marker_text = f"Marker {len(self.map_widget.canvas_marker_list) + 1}"
        self.map_widget.set_marker(position[0], position[1], text=marker_text)
        
    def clear_all_markers(self) -> None:
        #Remove all markers from the map.
        for marker in self.map_widget.canvas_marker_list:
            marker.delete()
    def __init__(self, parent, width: int = 400, height: int = 250):
        #Initialise the map widget with specified dimensions.
        
       #Args: parent: The parent widget, width (int): Width of the map widget in pixels, height (int): Height of the map widget in pixels
        super().__init__(parent)
        
        #Configure the map widget appearance
        self.configure(fg_color="#2a2a2a", corner_radius=6, border_width=1, border_color="#000000")
        
        #Set up grid configuration for proper widget layout
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=0)  
        self.grid_rowconfigure(2, weight=1)  
        self.grid_columnconfigure(0, weight=1)  
        
        #Initialise all map components
        self.setup_geocoder()
        self.setup_map(width, height)
        self.setup_map_controls()

class OutingPlanner:
    #Core planning engine that handles location search, distance calculation,
    #and itinerary generation for outings.
    
    def __init__(self):
        #Initialise the outing planner with geocoding capabilities.
        self.geocoder = Nominatim(user_agent="outerinator_app/1.0")
        self.geocode_cache = {}
        
    def geocode_location(self, location_name: str) -> Tuple[float, float]:
        #Check cache first
        if location_name in self.geocode_cache:
            return self.geocode_cache[location_name]
        
        try:
            location = self.geocoder.geocode(location_name)
            if location:
                coords = (location.latitude, location.longitude)
                self.geocode_cache[location_name] = coords
                return coords
        except Exception:
            pass
        
        default = (-36.8509, 174.7645)
        self.geocode_cache[location_name] = default
        return default
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        #Calculate great-circle distance between two points using Haversine formula.
        #Accounts for Earth's curvature for accurate distance measurement.
        
        #Args: lat1 (float): Starting point latitude, lon1 (float): Starting point longitude, lat2 (float): Ending point latitude, lon2 (float): Ending point longitude
            
        #Returns: float: Distance in kilometers
            
        R = 6371  #Earth's radius in kilometers
        
        #Convert degrees to radians for trigonometric functions
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        #Haversine formula calculation
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c  #Distance in kilometers
    
    def query_osm_places(self, center_lat: float, center_lon: float, radius_km: float, tags: List[str]) -> List[Dict]:
    #Query OpenStreetMap Overpass API for places within radius_km
    #that match any of the given tag filters.
    
    #Args: center_lat (float): Latitude of the center point, center_lon (float): Longitude of the center point, radius_km (float): Search radius in kilometers, tags (List[str]): List of OSM tag patterns to filter places
    
        try:
            radius_deg = radius_km / 111.0
            min_lat, max_lat = center_lat - radius_deg, center_lat + radius_deg
            min_lon = center_lon - radius_deg / math.cos(math.radians(center_lat))
            max_lon = center_lon + radius_deg / math.cos(math.radians(center_lat))

            #Build Overpass query for ALL tag patterns from ALL selected categories
            overpass_parts = []
        
            #Process each tag category
            for tag_category in tags:
                #Split by | to get individual tags
                individual_tags = tag_category.split('|')
                
                for tag_part in individual_tags:
                    tag_part = tag_part.strip()
                    if '=' in tag_part:
                        key, value = tag_part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                    
                        #Add queries for nodes, ways, and relations
                        overpass_parts.append(
                            f'node["{key}"="{value}"]({min_lat},{min_lon},{max_lat},{max_lon});'
                        )
                        overpass_parts.append(
                            f'way["{key}"="{value}"]({min_lat},{min_lon},{max_lat},{max_lon});'
                        )
                        overpass_parts.append(
                            f'relation["{key}"="{value}"]({min_lat},{min_lon},{max_lat},{max_lon});'
                        )

            if not overpass_parts:
                return []

            #Combine all parts into a single union query
            overpass_query = "[out:json][timeout:30];(" + "".join(overpass_parts) + ");out center;"
        
            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data=overpass_query,
                headers={'User-Agent': 'OuterinatorApp/1.0'},
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get('elements', [])
            else:
                return []

        except Exception:
            return []
    
    def estimate_activity_duration(self, place_type: str) -> float:
        #Estimate typical duration for different types of activities.
        
        #Args: place_type (str): Type of place/activity
            
        #Returns: float: Estimated duration in hours
        
        #Duration mapping for common activity types
        duration_map = {
            'park': 2.0, 'garden': 1.5, 'viewpoint': 0.5,
            'restaurant': 1.5, 'cafe': 1.0, 'bar': 2.0,
            'cinema': 3.0, 'theatre': 2.5,
            'museum': 2.0, 'gallery': 1.5, 'library': 1.0,
            'playground': 1.0, 'sports_centre': 2.0,
            'zoo': 3.0, 'aquarium': 2.0,
            'mall': 2.0, 'shop': 1.0,
            'arcade': 2.0, 'adventure_park': 3.0
        }
        
        #Find matching duration or return default
        for key, duration in duration_map.items():
            if key in place_type:
                return duration
                
        return 1.5  #Default duration for unknown types
    
    def create_optimal_itinerary(self, places: List[Dict], start_coords: Tuple[float, float], outing_start: datetime, outing_end: datetime) -> List[Dict]:
    #Create optimized itinerary considering travel time and activity duration.
    #Ensures diversity by mixing different place categories.
    
    #Args: places (List[Dict]): Available places to visit, start_coords (Tuple[float, float]): Starting location coordinates, outing_start (datetime): Outing start time, outing_end (datetime): Outing end time
        
    #Returns: List[Dict]: Optimized itinerary with timing information

        if not places:
            return []
    
        itinerary = []
        current_time = outing_start
        current_location = start_coords

        #Filter and categorise places
        places_by_category = {}

        for place in places:
            place_name = place.get('tags', {}).get('name', '')
            if not place_name or place_name in ['', 'None', 'null']:
                continue
                
            place_coords = self.get_place_coordinates(place)
            if not place_coords:
                continue
                
            straight_distance = self.calculate_distance(start_coords[0], start_coords[1], place_coords[0], place_coords[1])
            realistic_distance = straight_distance * 1.4

            place_type = self.get_place_type(place)

            if place_type not in places_by_category:
                places_by_category[place_type] = []

            places_by_category[place_type].append({
                'place': place,
                'distance': realistic_distance,
                'coords': place_coords,
                'type': place_type,
                'name': place_name
            })

        #Sort each category by distance, then shuffle top candidates
        for category in places_by_category:
            places_by_category[category].sort(key=lambda x: x['distance'])

            #Shuffle the top 10 closest places in each category
            #This gives variety while still favoring nearby places
            if len(places_by_category[category]) > 3:
                top_section = places_by_category[category][:10]
                rest_section = places_by_category[category][10:]
                random.shuffle(top_section)
                places_by_category[category] = top_section + rest_section

        #Remove duplicates and create diversified list
        seen_names = set()
        unique_places = []

        categories = list(places_by_category.keys())
        #Shuffle category order so we don't always start with same type
        random.shuffle(categories)
    
        max_iterations = max(len(v) for v in places_by_category.values()) if places_by_category else 0
    
        for i in range(max_iterations):
            for category in categories:
                if i < len(places_by_category[category]):
                    place_data = places_by_category[category][i]
                    if place_data['name'] not in seen_names:
                        seen_names.add(place_data['name'])
                        unique_places.append(place_data)
    
        #Build itinerary from diversified list of places from chosen categories
        for place_data in unique_places:
            if current_time >= outing_end:
                break

            #Calculate distance
            distance = self.calculate_distance(current_location[0], current_location[1], place_data['coords'][0], place_data['coords'][1])

            #Apply apply a multiplier to account for roads because I cannot use road maps
            realistic_distance = distance * 1.4
            travel_time_hours = (realistic_distance / 25.0) + (5 / 60.0)
            travel_end_time = current_time + timedelta(hours=travel_time_hours)

            if travel_end_time >= outing_end:
                continue

            #Estimate time spent at the location
            activity_duration = self.estimate_activity_duration(place_data['type'])
            activity_end_time = travel_end_time + timedelta(hours=activity_duration)

            #Adjust if it exceeds outing time
            if activity_end_time > outing_end:
                remaining_time = (outing_end - travel_end_time).total_seconds() / 3600
                if remaining_time >= 0.5:
                    activity_duration = remaining_time
                    activity_end_time = outing_end
                else:
                    continue

            itinerary.append({
                'place': place_data['place'],
                'start_time': travel_end_time,
                'end_time': activity_end_time,
                'activity': place_data['name'],
                'type': place_data['type'],
                'duration': activity_duration,
                'travel_time': travel_time_hours,
                'coordinates': place_data['coords'],
                'distance': realistic_distance
            })

            current_time = activity_end_time
            current_location = place_data['coords']

            #Limit activities by available time
            total_hours = (outing_end - outing_start).total_seconds() / 3600
            max_activities = min(8, max(3, int(total_hours / 1.5)))

            if len(itinerary) >= max_activities:
                break
        return itinerary

    def get_place_coordinates(self, place: Dict) -> Optional[Tuple[float, float]]:
        #Extract coordinates from OpenStreetMap place data.
        #Handles different OSM element types (node, way, relation).
        
        #Args: place (Dict): OSM place data
            
        #Returns: Optional[Tuple[float, float]]: Coordinates or None if unavailable
        
        if 'lat' in place and 'lon' in place:
            return place['lat'], place['lon']
        elif 'center' in place:
            return place['center']['lat'], place['center']['lon']
        elif 'bounds' in place:
            #Calculate center point from bounding box
            bounds = place['bounds']
            lat = (bounds['minlat'] + bounds['maxlat']) / 2
            lon = (bounds['minlon'] + bounds['maxlon']) / 2
            return lat, lon
        return None
    
    def get_place_type(self, place: Dict) -> str:
        #Determine place type from OpenStreetMap tags.
        
        #Args: place (Dict): OSM place data with tags
            
        #Returns: str: Place type identifier
        
        tags = place.get('tags', {})
        #Check common OSM tag categories for place type
        for key in ['leisure', 'amenity', 'tourism', 'shop', 'sport']:
            if key in tags:
                return tags[key]
        return 'unknown'


class OpeningFrame(ctk.CTkFrame):
    #Initial application frame displaying welcome screen and navigation options.
    #Provides entry points to SignIn and signup functionality.
    
    def __init__(self, parent, controller):
        #Initialise the opening frame with branding and navigation.
        
        #Args: parent: Parent widget, controller: Main application controller for frame navigation
        
        super().__init__(parent)
        self.controller = controller
        
        #Configure frame with brand color scheme
        self.configure(fg_color="#00199c")
        
        #Configure grid layout for responsive design
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(2, weight=2)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
            
        #Application title label
        label = ctk.CTkLabel(self, text="Welcome to Outerinator", text_color="#d78adf", font=("Open Sans", 30))
        label.grid(row=0, column=0, pady=20, padx=10, columnspan=2, sticky="ew")
        
        #Load and display application logo
        try:
            #Construct path to logo image
            script_directory = path.dirname(path.abspath(__file__))
            logo_path = path.join(script_directory, "Outerinator_Logo.png")

            #Create CTkImage object from logo file
            self.logo_image = ctk.CTkImage(Image.open(logo_path), size=(200, 200))
            image_label = ctk.CTkLabel(self, image=self.logo_image, text="")
            image_label.grid(row=1, column=0, columnspan=2, pady=20)
            
        except Exception as e:
            #Display placeholder if logo loading fails
            image_placeholder = ctk.CTkLabel(self, text="Logo Image Not Found", font=("Arial", 16), fg_color="#ff0000")
            image_placeholder.grid(row=1, column=0, columnspan=2, pady=20)
        
        #Frame to hold navigation buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 20))

        #Frame to go to SignIn page
        SignIn_button = ctk.CTkButton(button_frame, text="🔑 Sign In", command=lambda: controller.show_frame("SigninFrame"), fg_color="#007acc", hover_color="#005a99", width=140, height=40, corner_radius=12)
        SignIn_button.pack(side="left", padx=(0, 10))

        #Frame to go to signup page
        signup_button = ctk.CTkButton(button_frame, text="🆕 Sign Up", command=lambda: controller.show_frame("SignUpFrame"), fg_color="#00cc00", hover_color="#009900", width=140, height=40, corner_radius=12)
        signup_button.pack(side="left")

class SigninFrame(ctk.CTkFrame):
    #User authentication frame for existing users to log into the application.
    #Handles credential validation and user session initiation.

    def clear_SignIn_fields(self) -> None:
        #Clear all input fields and error messages in the SignIn form.
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.error_label.configure(state="normal")
        self.error_label.delete("1.0", tk.END)
        self.error_label.configure(state="disabled")
    
    def SignIn(self) -> None:
    #Validate user credentials and initiate SignIn process.
        username = self.username_entry.get()
        password = self.password_entry.get()
    
        #Validate if username is empty or not
        if not username:
            self.display_error("Please enter username")
            return
    
        #Use context manager for automatic connection cleanup
        with sqlite3.connect('outerinator.db', timeout=10) as connection:
            cursor = connection.cursor()

            #Query database for user credentials AND user_id
            cursor.execute("SELECT id, password_hash, theme FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()

        #Validate password match
        if user_data and user_data[1] == password:
            self.controller.current_user_id = user_data[0]
            self.controller.current_username = username
    
            #Load user's theme preference
            user_theme = user_data[2] if len(user_data) > 2 and user_data[2] else "dark"
            self.controller.apply_theme(user_theme)
    
            self.display_success("SignIn successful!")
            
            #Navigate to main page after successful SignIn
            self.error_label.after(1000, lambda: self.controller.show_frame("MainPageFrame"))
            self.error_label.after(3000, self.clear_SignIn_fields)
            
            main_frame = self.controller.frames.get("MainPageFrame")
            if main_frame:
                #Refresh plans and calendar immediately
                main_frame.refresh_plans()
                #Redraw calendar so plan markers appear
                if hasattr(main_frame, "draw_calendar"):
                    main_frame.draw_calendar()

        #Handle incorrect password
        elif user_data:
            self.display_error("Incorrect password.")
            return

        #Handle non-existent username
        else:
            self.display_error("Username not found.")
            return
            
    def toggle_password(self) -> None:
        #Toggle password visibility in the password entry field.
        if self.show_password:
            #Hide password (show asterisks)
            self.password_entry.configure(show="*")
            self.eye_image.configure(text="👁️")
            self.show_password = False
        else:
            #Show password (plain text)
            self.password_entry.configure(show="")
            self.show_password = True
    
    def display_error(self, message: str) -> None:
        #Display error message in the error label.
        
        #Args: message (str): Error message to display
        
        self.error_label.configure(state="normal")
        self.error_label.delete("1.0", tk.END)
        self.error_label.insert("1.0", message)
        self.error_label.configure(state="disabled")
    
    def display_success(self, message: str) -> None:
        #Display success message in the error label.
        
        #Args: message (str): Success message to display
        self.error_label.configure(state="normal")
        self.error_label.delete("1.0", tk.END)
        self.error_label.insert("1.0", message)
        self.error_label.configure(state="disabled")
            
    def __init__(self, parent, controller):
        #Initialise the signin frame with SignIn form elements.
        
        #Args: parent: Parent widget, controller: Main application controller
        super().__init__(parent)
        self.controller = controller
        
        #Configure frame appearance
        self.configure(fg_color="#00199c")
        
        #Configure responsive grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1) 
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        #Frame title
        label = ctk.CTkLabel(self, text="Sign In", text_color="#d78adf", font=("Arial", 24))
        label.grid(row=0, column=0, columnspan=2, pady=20)
        
        #Username input section
        username_label = ctk.CTkLabel(self, text="Username:", text_color="#d78adf")
        username_label.grid(row=1, column=0, pady=5)
        
        self.username_entry = ctk.CTkEntry(self, width=200)
        self.username_entry.grid(row=2, column=0, pady=5)
        
        #Password input section
        password_label = ctk.CTkLabel(self, text="Password:", text_color="#d78adf")
        password_label.grid(row=3, column=0, pady=5)
        
        self.password_entry = ctk.CTkEntry(self, show="*", width=200)
        self.password_entry.grid(row=4, column=0, pady=5)
        
        #Password visibility toggle
        self.show_password = False
        self.eye_image = ctk.CTkButton(self, text="👁️", width=28, height=24, fg_color="transparent", bg_color="#f9f9fa", text_color="#d78adf", font=("Segoe UI Emoji", 14), command=self.toggle_password)
        self.eye_image.place(in_=self.password_entry, relx=1.0, x=-5, rely=0.5, anchor="e")

        #Error/success message display
        self.error_label = ctk.CTkTextbox(self, wrap="word", height=50, width=200, state="disabled", fg_color="#00199c", text_color="#ff0000")
        self.error_label.grid(row=2, column=1, pady=5)
        
        #Frame to hold navigation buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))

        #SignIn button
        SignIn_button = ctk.CTkButton(button_frame, text="✅ Sign In", command=self.SignIn, fg_color="#007acc", hover_color="#005a99", width=120, corner_radius=10)
        SignIn_button.pack(side="left", padx=(0, 10))

        #Back to opening screen button
        back_button = ctk.CTkButton(button_frame, text="⬅ Back", command=lambda: controller.show_frame("OpeningFrame"), fg_color="#cc0000", hover_color="#990000", width=100, corner_radius=10)
        back_button.pack(side="left")

class SignUpFrame(ctk.CTkFrame):
    #User registration frame for new users to create accounts.
    #Handles username availability checking and password validation.
    
    def clear_signup_fields(self) -> None:
        #Clear all input fields and result messages.
        self.result_label.configure(state="normal")
        self.result_label.delete("1.0", tk.END)
        self.result_label.configure(state="disabled")
        
    def toggle_password(self) -> None:
        #Toggle password visibility in the registration form.
        if self.show_password:
            self.new_password_entry.configure(show="*")
            self.eye_image.configure(text="👁️")
            self.show_password = False
        else:
            self.new_password_entry.configure(show="")
            self.show_password = True
            
    def signup(self) -> None:
        #Process user registration with comprehensive validation.
        username = self.new_username_entry.get()
        password = self.new_password_entry.get()

        #Use context manager for database connection
        with sqlite3.connect('outerinator.db', timeout=10) as connection:
            cursor = connection.cursor()
            
            #Comprehensive password validation
            validation_errors = self.validate_password(password)
            if validation_errors:
                self.display_result(validation_errors)
                self.new_password_entry.delete(0, tk.END)
                return
        
            #Check username availability
            existing_user = cursor.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
        
            if existing_user:
                self.display_result("Username already exists. Please choose another.")
                self.clear_password_field()
                return

            #Save new user to database
            try:
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
                connection.commit()
                self.display_success("Password is valid and user saved! Please return to the Sign In tab.")
                self.clear_password_field()
                self.result_label.after(3000, self.clear_signup_fields)
            except Exception as e:
                self.display_result(f"Registration error: {str(e)}")
    
    def validate_password(self, password: str) -> Optional[str]:
        #Validate password against security requirements.
        
        #Args: password (str): Password to validate
            
        #Returns: Optional[str]: Error message if invalid, None if valid
        
        if not password:
            return "Please enter a password"
        elif len(password) <= 8:
            return "Password must be more than 8 characters"
        elif not re.search("[a-z]", password):
            return "Password must contain at least one lowercase letter"
        elif not re.search("[A-Z]", password):
            return "Password must contain at least one uppercase letter"
        elif not re.search("[0-9]", password):
            return "Password must contain at least one number"
        elif not re.search("[_@!$?]", password):
            return "Password must contain at least one special character (_@!$?)"
        elif re.search(r"\s", password):
            return "Password must not contain spaces"
        return None
    
    def clear_password_field(self) -> None:
        #Clear the password entry field.
        self.new_password_entry.delete(0, tk.END)
        self.new_username_entry.delete(0, tk.END)
    
    def display_result(self, message: str) -> None:
        #Display result message in the result label.
        
        #Args: message (str): Message to display
            
        self.result_label.configure(state="normal")
        self.result_label.delete("1.0", tk.END)
        self.result_label.insert("1.0", message)
        self.result_label.configure(state="disabled")
    
    def display_success(self, message: str) -> None:
        #Display success message in the result label.
        
        #Args: message (str): Success message to display
            
        self.result_label.configure(state="normal")
        self.result_label.delete("1.0", tk.END)
        self.result_label.insert("1.0", message)
        self.result_label.configure(state="disabled")
            
    def __init__(self, parent, controller):
        #Initialise the signup frame with registration form elements.
        
        #Args: parent: Parent widget, controller: Main application controller
        
        super().__init__(parent)
        self.controller = controller
        
        #Configure frame appearance
        self.configure(fg_color="#318ccd")
        
        #Configure responsive grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        #Frame title
        label = ctk.CTkLabel(self, text="Sign Up", text_color="#8c009c", font=("Arial", 24))
        label.grid(row=0, column=0, columnspan=2, pady=20, sticky="ew")
        
        #Username input section
        new_username_label = ctk.CTkLabel(self, text="Choose a Username:", text_color="#8c009c")
        new_username_label.grid(row=1, column=0, pady=5, sticky="nsew")
        self.new_username_entry = ctk.CTkEntry(self, width=200)
        self.new_username_entry.grid(row=2, column=0, pady=5)
        
        #Password input section
        new_password_label = ctk.CTkLabel(self, text="Choose a Password:", text_color="#8c009c")
        new_password_label.grid(row=3, column=0, pady=5, sticky="nsew")
        
        self.new_password_entry = ctk.CTkEntry(self, show="*", width=200)
        self.new_password_entry.grid(row=4, column=0, pady=5)
        
        #Password visibility toggle
        self.show_password = False
        self.eye_image = ctk.CTkButton(self, text="👁️", width=28, height=24,fg_color="transparent", bg_color="#f9f9fa", text_color="#8c009c", font=("Segoe UI Emoji", 14), command=self.toggle_password)
        self.eye_image.place(in_=self.new_password_entry, relx=1.0, x=-5, rely=0.5, anchor="e")
        
        #Result message display
        self.result_label = ctk.CTkTextbox(self, wrap="word", height=50, width=200, state="disabled", fg_color="#318ccd", text_color="#ff0000")
        self.result_label.grid(row=2, column=1, pady=10, sticky="nsew")
        
        #Frame to hold navigation buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))

        #Sign up button
        signup_button = ctk.CTkButton(button_frame, text="📝 Sign Up", command=self.signup, fg_color="#00cc00", hover_color="#009900", width=120, corner_radius=10)
        signup_button.pack(side="left", padx=(0, 10))

        #Back to opening screen button
        back_button = ctk.CTkButton(button_frame, text="⬅ Back", command=lambda: controller.show_frame("OpeningFrame"), fg_color="#cc0000", hover_color="#990000", width=100, corner_radius=10)
        back_button.pack(side="left")

class MainPageFrame(ctk.CTkFrame):
    #Main application dashboard after successful SignIn.
    #Provides access to core features and navigation.
    
    def go_to_planning(self):
        #Navigate to planning frame
        self.controller.show_frame("PlanningFrame")
    
    def setup_calendar(self, parent):
        #Setup the calendar widget
        self.calendar_frame = ctk.CTkFrame(parent, fg_color="#3a4044", corner_radius=6, border_width=1, border_color="#000000")
        self.calendar_frame.grid(row=1, column=0, sticky="nsew", pady=(1, 3))
        
        #Calendar header
        calendar_header = ctk.CTkLabel(self.calendar_frame, text="📅 Calendar", font=("Arial", 12, "bold"), text_color="white")
        calendar_header.pack(pady=(8, 5))
        
        #Get current date
        today = date.today()
        self.current_month = today.month
        self.current_year = today.year
        
        #Month/Year display and navigation
        nav_frame = ctk.CTkFrame(self.calendar_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=5, pady=5)
        
        #Previous month button
        prev_btn = ctk.CTkButton(nav_frame, text="◀", width=30, height=25, command=self.prev_month, fg_color="#2a2a2a", hover_color="#404040")
        prev_btn.pack(side="left")
        
        #Month/Year label
        self.month_year_label = ctk.CTkLabel(nav_frame, text=f"{calendar.month_name[self.current_month]} {self.current_year}", font=("Arial", 11, "bold"))
        self.month_year_label.pack(side="left", expand=True)
        
        #Next month button
        next_btn = ctk.CTkButton(nav_frame, text="▶", width=30, height=25, command=self.next_month, fg_color="#2a2a2a", hover_color="#404040")
        next_btn.pack(side="right")
        
        #Calendar grid container
        self.calendar_grid = ctk.CTkFrame(self.calendar_frame, fg_color="transparent")
        self.calendar_grid.pack(fill="both", expand=True, padx=5, pady=5)
        
        #Draw the calendar
        self.draw_calendar()
    
    def draw_calendar(self):
        #Draw the calendar grid for current month.
        #Clear existing calendar
        for widget in self.calendar_grid.winfo_children():
            widget.destroy()
        
        #Update month/year label
        self.month_year_label.configure(text=f"{calendar.month_name[self.current_month]} {self.current_year}")
        
        #Day headers
        days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
        for i, day in enumerate(days):
            label = ctk.CTkLabel(
                self.calendar_grid, 
                text=day, 
                font=("Arial", 9, "bold"),
                width=20,
                height=20
            )
            label.grid(row=0, column=i, padx=1, pady=1)
        
        #Get calendar data
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = date.today()
        
        #Load user's plan dates
        plan_dates = self.get_user_plan_dates()
        
        #Draw days
        for week_num, week in enumerate(cal, start=1):
            for day_num, day in enumerate(week):
                if day == 0:
                    #Empty cell
                    empty = ctk.CTkLabel(self.calendar_grid, text="", width=20, height=20)
                    empty.grid(row=week_num, column=day_num, padx=1, pady=1)
                else:
                    #Check if this day has plans
                    current_date = date(self.current_year, self.current_month, day)
                    has_plan = current_date in plan_dates
                    
                    #Check if it's today
                    is_today = (day == today.day and 
                               self.current_month == today.month and 
                               self.current_year == today.year)
                    
                    #Set colors
                    if is_today:
                        fg_color = "#4CAF50"
                        text_color = "white"
                    elif has_plan:
                        fg_color = "#FF9800"
                        text_color = "white"
                    else:
                        fg_color = "#2a2a2a"
                        text_color = "#cccccc"
                    
                    day_btn = ctk.CTkButton(self.calendar_grid, text=str(day), width=20, height=20, fg_color=fg_color, hover_color="#404040", text_color=text_color, font=("Arial", 9), command=self.create_day_click_handler(day))
                    day_btn.grid(row=week_num, column=day_num, padx=1, pady=1)
    
    def create_day_click_handler(self, day):
        #Create a click handler for a specific day
        return lambda: self.on_day_click(day)
    
    def prev_month(self):
        #Go to previous month
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.draw_calendar()
    
    def next_month(self):
        #Go to next month
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.draw_calendar()
    
    def on_day_click(self, day):
        #Handle calendar day click.
        selected_date = date(self.current_year, self.current_month, day)
        #Show plans for this date
        self.show_plans_for_date(selected_date)

    def get_user_plan_dates(self):
        #Get all dates that have plans for the current user.
        if not getattr(self.controller, "current_user_id", None):
            return set()
        
        try:
            with sqlite3.connect("outerinator.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT date FROM plans 
                    WHERE user_id = ?
                """, (self.controller.current_user_id,))
                
                dates = set()
                for row in cursor.fetchall():
                    try:
                        plan_date = datetime.strptime(row[0], "%Y-%m-%d").date()
                        dates.add(plan_date)
                    except:
                        pass
                
                return dates
        except Exception as e:
            return set()
    
    def setup_plans_viewer(self, parent):
        #Setup the plans viewer widget
        self.plans_frame = ctk.CTkFrame(parent, fg_color="#3eaef9", corner_radius=6, border_width=1, border_color="#000000")
        self.plans_frame.grid(row=2, column=0, sticky="nsew", pady=(3, 0))
        
        #Plans header
        plans_header = ctk.CTkLabel(self.plans_frame, text="📋 Your Plans", font=("Arial", 12, "bold"), text_color="white")
        plans_header.pack(pady=(8, 5))
        
        #Scrollable plans list
        self.plans_list = ctk.CTkScrollableFrame(self.plans_frame, fg_color="#2a2a2a", height=150)
        self.plans_list.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        #Load plans
        self.refresh_plans()
    
    def refresh_plans(self):
        #Refresh the plans list
        #Clear existing plans
        for widget in self.plans_list.winfo_children():
            widget.destroy()
        
        if not self.controller.current_user_id:
            no_plans = ctk.CTkLabel(self.plans_list, text="Please log in to view plans", font=("Arial", 10), text_color="#cccccc")
            no_plans.pack(pady=20)
            return
        
        #Load plans from database
        plans = self.load_user_plans()
        
        if not plans:
            no_plans = ctk.CTkLabel(self.plans_list, text="No plans yet!\nCreate your first outing!", font=("Arial", 10), text_color="#cccccc")
            no_plans.pack(pady=20)
            return
        
        #Display each plan
        for plan in plans:
            plan_id, plan_name, start_location, plan_date, start_time, end_time, created_at = plan
            
            #Create plan item frame
            plan_frame = ctk.CTkFrame(self.plans_list, fg_color="#1a1a1a", corner_radius=4)
            plan_frame.pack(fill="x", pady=3, padx=3)
            
            #Truncate location if too long
            display_location = start_location[:20] + "..." if len(start_location) > 20 else start_location
            
            #Plan button (clickable)
            plan_btn = ctk.CTkButton(plan_frame, text=f"{plan_name}\n📍 {display_location}\n📅 {plan_date}", fg_color="#1a1a1a", hover_color="#3a3a3a", text_color="white", anchor="w", height=60, font=("Arial", 9), command=self.create_view_plan_handler(plan_id))
            plan_btn.pack(side="left", fill="both", expand=True)
            
            #Delete button
            delete_btn = ctk.CTkButton(plan_frame, text="🗑️", width=30, height=60, fg_color="#cc0000", hover_color="#990000", command=self.create_delete_plan_handler(plan_id))
            delete_btn.pack(side="right", padx=2)
    
    def create_view_plan_handler(self, plan_id):
        #Create handler for viewing a plan
        return lambda: self.view_plan_details(plan_id)
    
    def show_delete_confirmation_by_id(self, plan_id, popup):
        #Show a confirmation popup before deleting a plan by id.
        confirm_popup = ctk.CTkToplevel(self)
        confirm_popup.title("Confirm Delete")
        confirm_popup.geometry("350x160")
        confirm_popup.transient(popup)
        confirm_popup.grab_set()

        label = ctk.CTkLabel(confirm_popup, text="Are you sure you want to delete this plan?", wraplength=300)
        label.pack(pady=(20, 10))

        button_frame = ctk.CTkFrame(confirm_popup, fg_color="transparent")
        button_frame.pack(pady=10)

        #Confirm and cancel buttons
        confirm_btn = ctk.CTkButton(button_frame, text="Delete", fg_color="#b30000", hover_color="#800000", command=lambda pid=plan_id, pop=popup, cpop=confirm_popup: self.delete_plan_by_id(pid, pop, cpop))
        confirm_btn.grid(row=0, column=0, padx=10)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=confirm_popup.destroy)
        cancel_btn.grid(row=0, column=1, padx=10)

    def delete_plan_by_id(self, plan_id, popup, confirm_popup):
        #Delete the plan record with id=plan_id, close popups and refresh UI.
        with sqlite3.connect("outerinator.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
            conn.commit()
        #Close popups and refresh
        if confirm_popup:
            confirm_popup.destroy()
        if popup:
            popup.destroy()
        self.refresh_plans()
        self.draw_calendar()
                
    def create_delete_plan_handler(self, plan_id):
        #Create handler for deleting a plan
        return lambda: self.delete_plan(plan_id)
    
    def load_user_plans(self):
        #Load all plans for the current user
        if not self.controller.current_user_id:
            return []
        
        try:
            with sqlite3.connect("outerinator.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, plan_name, start_location, date, start_time, end_time, created_at
                    FROM plans
                    WHERE user_id = ?
                    ORDER BY date DESC, created_at DESC
                    LIMIT 10
                """, (self.controller.current_user_id,))
                
                return cursor.fetchall()
        except Exception as e:
            return []
    
    def view_plan_details(self, plan_id):
        #View details of a specific plan
        with sqlite3.connect("outerinator.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT plan_name, start_location, date, start_time, end_time, details
                FROM plans WHERE id = ?
            """, (plan_id,))
            
            plan = cursor.fetchone()
                
            if plan:
                plan_name, start_location, plan_date, start_time, end_time, details = plan
                self.show_plan_popup(plan_id, plan_name, start_location, plan_date, start_time, end_time, details)
    
    def show_plan_popup(self, plan_id, plan_name, start_location, plan_date, start_time, end_time, details):
        #Show plan details in a popup.
        popup = ctk.CTkToplevel(self)
        popup.title(f"Plan Details: {plan_name}")
        popup.geometry("500x400")
        
        #Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (500 // 2)
        y = (popup.winfo_screenheight() // 2) - (400 // 2)
        popup.geometry(f"500x400+{x}+{y}")
        
        popup.transient(self)
        popup.grab_set()
        
        #Header
        header = ctk.CTkFrame(popup, fg_color="#3eaef9", corner_radius=0)
        header.pack(fill="x")
        
        title = ctk.CTkLabel(header, text=f"📋 {plan_name}", font=("Open Sans", 16, "bold"), text_color="white")
        title.pack(pady=15)
        
        #Content
        content = ctk.CTkScrollableFrame(popup, fg_color="#2a2a2a")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        
        #Plan info
        info_text = f"""📍 Starting Location: {start_location}
📅 Date: {plan_date}
⏰ Time: {start_time} - {end_time}

🗓️ Itinerary:
{details}"""
        
        info_label = ctk.CTkLabel(content, text=info_text, font=("Open Sans", 11), justify="left", anchor="w")
        info_label.pack(fill="both", padx=10, pady=10)
        
        #Close button
        close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy, fg_color="#007acc", hover_color="#005a99", height=40, font=("Open Sans", 12, "bold"))
        close_btn.pack(pady=10, padx=20, fill="x")
        
        # Delete Plan button
        delete_button = ctk.CTkButton(popup, text="🗑️ Delete This Plan", fg_color="#b30000", hover_color="#800000", command=lambda pid=plan_id, pop=popup: self.show_delete_confirmation_by_id(pid, pop))
        delete_button.pack(pady=(10, 20))
    
    def show_plans_for_date(self, selected_date):
        if not self.controller.current_user_id:
            return

        with sqlite3.connect("outerinator.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, plan_name, start_location, start_time, end_time, details
                FROM plans
                WHERE user_id = ? AND date = ?
            """, (self.controller.current_user_id, selected_date.strftime("%Y-%m-%d")))

            plans = cursor.fetchall()

        if plans:
            plan_id, plan_name, start_location, start_time, end_time, details = plans[0]
            plan_date = selected_date.strftime("%Y-%m-%d")
            self.show_plan_popup(plan_id, plan_name, start_location, plan_date, start_time, end_time, details)
        else:
            self.show_info_popup("No Plans", f"No plans scheduled for {selected_date.strftime('%d %B %Y')}")
 

    def show_info_popup(self, title, message):
        #Show info popup
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("350x150")
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (350 // 2)
        y = (popup.winfo_screenheight() // 2) - (150 // 2)
        popup.geometry(f"350x150+{x}+{y}")
        
        popup.transient(self)
        popup.grab_set()
        
        label = ctk.CTkLabel(popup, text=message, font=("Open Sans", 12), wraplength=300)
        label.pack(pady=30)
        
        ok_btn = ctk.CTkButton(popup, text="OK", command=popup.destroy, width=100)
        ok_btn.pack(pady=10)
        
    def change_appearance_mode(self, mode):
        #Change the appearance mode safely
        self.after(100, lambda: ctk.set_appearance_mode(mode.lower()))
        self.after(100, lambda: self.show_info_popup("Theme Changed", f"Switched to {mode} mode."))
        if self.controller.current_user_id:
            threading.Thread(
                target=self.controller.apply_theme,
                args=(mode.lower(),),
                daemon=True
            ).start()
    
    def choose_main_colour(self):
    #Choose a new main colour using a colour picker.
        color_code = colorchooser.askcolor(title="Pick Main Colour")[1]
        if not color_code:
            return

        #Apply new colour immediately
        self.controller.apply_main_colour(color_code)
        self.main_colour_button.configure(fg_color=color_code)

        #Save colour preference in background
        if getattr(self.controller, "current_user_id", None):
            thread = threading.Thread(
                target=self.controller.save_main_colour_preference,
                args=(color_code,),
                daemon=True
            )
            thread.start()
        
    def change_colour_theme(self, theme):
        #Apply color theme safely
        theme_map = {
            "blue": "blue",
            "green": "green",
            "dark-blue": "blue"
        }
        key = theme.lower().strip()
        chosen = theme_map.get(key, "blue")

        #Apply theme
        self.after(0, lambda: ctk.set_default_color_theme(chosen))
        self.after(200, lambda: self.show_info_popup("Theme Changed", "Color theme applied successfully."))

        #Save to DB in background
        if getattr(self.controller, "current_user_id", None):
            threading.Thread(
                target=self.save_user_button_theme_preference,
                args=(chosen,),
                daemon=True
            ).start()

    def save_user_button_theme_preference(self, theme_value):
    #Save the theme preference to the database.
        with sqlite3.connect("outerinator.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET theme = ? WHERE id = ?",
                (theme_value, self.controller.current_user_id)
            )
            conn.commit()
    
    def show_options_menu(self):
        popup = ctk.CTkToplevel(self)
        popup.title("⚙️ Options")
        popup.geometry("450x450")

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (450 // 2)
        y = (popup.winfo_screenheight() // 2) - (450 // 2)
        popup.geometry(f"450x450+{x}+{y}")

        popup.transient(self)
        popup.grab_set()

        header = ctk.CTkFrame(popup, fg_color="#3eaef9", corner_radius=0)
        header.pack(fill="x")

        title = ctk.CTkLabel(header, text="⚙️ Settings & Options", font=("Open Sans", 18, "bold"), text_color="white")
        title.pack(pady=15)

        content = ctk.CTkFrame(popup, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        #Appearance Mode
        appearance_label = ctk.CTkLabel(content, text="Appearance Mode:", font=("Open Sans", 13, "bold"))
        appearance_label.pack(anchor="w", pady=(0, 5))

        appearance_menu = ctk.CTkOptionMenu(content, values=["Dark", "Light", "System"], command=self.change_appearance_mode, width=200)
        appearance_menu.set("Dark")
        appearance_menu.pack(anchor="w", pady=(0, 20))

        #Main Colour Picker
        self.main_colour_label = ctk.CTkLabel(content, text="Main Colour:", font=("Open Sans", 13, "bold"))
        self.main_colour_label.pack(anchor="w", pady=(0, 5))

        self.main_colour_button = ctk.CTkButton(content, text="Choose Colour", command=self.choose_main_colour, width=200)
        self.main_colour_button.pack(anchor="w", pady=(0, 20))
    
        #Theme Selection
        theme_label = ctk.CTkLabel(content, text="Color Theme:", font=("Open Sans", 13, "bold"))
        theme_label.pack(anchor="w", pady=(0, 5))

        theme_menu = ctk.CTkOptionMenu(content, values=["Blue", "Green", "Dark-Blue"], command=self.change_colour_theme, width=200)
        theme_menu.set(getattr(self.controller, "current_theme", "Blue").capitalize())
        theme_menu.pack(anchor="w", pady=(0, 20))

        #Account Info
        account_label = ctk.CTkLabel(content, text="Account Information:", font=("Open Sans", 13, "bold"))
        account_label.pack(anchor="w", pady=(0, 5))

        username_info = ctk.CTkLabel(content, text=f"👤 Username: {self.controller.current_username}", font=("Open Sans", 11))
        username_info.pack(anchor="w", pady=(0, 5))

        user_id_info = ctk.CTkLabel(content, text=f"🆔 User ID: {self.controller.current_user_id}", font=("Open Sans", 11))
        user_id_info.pack(anchor="w", pady=(0, 20))

        close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy, fg_color="#007acc", hover_color="#005a99", height=40, font=("Open Sans", 12, "bold"))
        close_btn.pack(pady=10)
    
    def logout(self):
        #Clear user session data on logout
        self.controller.current_user_id = None
        self.controller.current_username = None
        self.controller.show_frame("OpeningFrame")
        
    def __init__(self, parent, controller):
        #Initialize the main page with navigation and core features.
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=main_colour_theme)
        
        #Initialise variables
        self.plan_to_delete = None
        
        #Main page grid configuration
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        
        #Left sidebar column
        left_column = ctk.CTkFrame(self, fg_color="transparent", width=180)
        left_column.grid(row=0, column=0, rowspan=2, sticky="nswe", padx=(5, 3), pady=5)
        left_column.grid_propagate(False)
        
        #Left column grid configuration
        left_column.rowconfigure(0, weight=0) 
        left_column.rowconfigure(1, weight=1)
        left_column.rowconfigure(2, weight=1) 
        left_column.columnconfigure(0, weight=1)
        
        #Logout button
        self.logout_btn = ctk.CTkButton(left_column, text="🚪 Logout", command=self.logout, fg_color="#cc0000", hover_color="#990000", height=36, corner_radius=10)
        self.logout_btn.grid(row=0, column=0, padx=10, pady=(20, 8), sticky="ew")

        #Calendar widget
        self.setup_calendar(left_column)
        
        #Plans widget
        self.setup_plans_viewer(left_column)
        
        #Right column
        right_column = ctk.CTkFrame(self, fg_color="transparent")
        right_column.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=3, pady=5)
        right_column.rowconfigure(0, weight=0)
        right_column.rowconfigure(1, weight=1)
        right_column.columnconfigure(0, weight=1)
        
        #Application banner with primary actions
        self.banner = ctk.CTkFrame(right_column, fg_color="#3eaef9", corner_radius=6, border_width=1, border_color="#000000", height=50)
        self.banner.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        self.banner.grid_propagate(False)
        
        #Planning button
        self.planning_button = ctk.CTkButton(self.banner, text="🗓️  Plan an Outing", font=("Open Sans", 14, "bold"), text_color="white", width=150, height=36, corner_radius=10, command=self.go_to_planning)
        self.planning_button.pack(side="left", padx=10, pady=(8, 8))
        
        #Options button
        self.options_button = ctk.CTkButton(self.banner, text="⚙️ Options", font=("Open Sans", 14, "bold"), text_color="white", width=120, height=36, corner_radius=10, command=self.show_options_menu)
        self.options_button.pack(side="right", padx=10, pady=(8, 8))
        
        #Interactive map widget
        self.map_widget = MapWidget(right_column, width=400, height=250)
        self.map_widget.grid(row=1, column=0, sticky="nsew")

class PlanningFrame(ctk.CTkFrame):
    #Outing planning interface for creating customized activity itineraries.
    #Integrates location search, activity selection, and schedule planning.
    
    def set_start_location_from_map(self, lat: float, lon: float, name: str) -> None:
    #Set the starting location from map selection
    
    #Args: lat: Latitude, lon: Longitude, name: Location name
    
        self.start_coords = (lat, lon)
    
        #Truncate long names
        display_name = name if len(name) <= 50 else name[:47] + "..."
    
        self.start_loc_display.configure(text=f"📍 {display_name}", text_color="#4CAF50")

        self.show_message(f"Starting location set!", "success")
        
    def validate_planning_inputs(self) -> bool:
    #Validate all planning form inputs for completeness and correctness.
    
    #Returns: bool: True if all inputs are valid, False otherwise
    
        #Starting location validation
        if not self.start_coords:
            self.show_message("Please select your starting location using the map!", "error")
            return False
    
        #Tag selection validation
        if not self.selected_tags:
            self.show_message("Please select at least one activity category!", "error")
            return False
    
        #Distance validation
        distance = self.distance_entry.get().strip()
        if not distance:
            self.show_message("Please enter maximum travel distance", "error")
            return False
    
        try:
            dist = float(distance)
            if dist <= 0:
                self.show_message("Distance must be greater than 0 km", "error")
                return False
            if dist > 100:
                self.show_message("Distance must be 100 km or less", "error")
                return False
        except ValueError:
            self.show_message("Please enter a valid number for distance", "error")
            return False
    
        #Date validation
        if self.selected_date < date.today():
            self.show_message("Please select a date in the future!", "error")
            return False
    
        #Time range validation
        start = self.start_time.get()
        end = self.end_time.get()
    
        start_hour, start_minute = map(int, start.split(':'))
        end_hour, end_minute = map(int, end.split(':'))
    
        start_total = start_hour * 60 + start_minute
        end_total = end_hour * 60 + end_minute
    
        if start_total >= end_total:
            self.show_message("End time must be after start time", "error")
            return False
    
        if (end_total - start_total) < 30:
            self.show_message("Outing must be at least 30 minutes", "error")
            return False
    
        return True
    
    def return_to_main(self):
    #Return to main page and reset the planner.
        self.start_loc_display.configure(text=f"📍 No location selected", text_color="#4CAF50")
        self.date_entry.set_date(datetime.now().date()) if hasattr(self, "date_entry") else None
        self.selected_date = None
        self.selected_locations = []
        self.activities_listbox.delete(0, "end") if hasattr(self, "activities_listbox") else None
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        for tag in self.selected_tags:
            self.tag_buttons[tag].configure(fg_color="#2a2a2a")
        self.selected_tags=[]
        self.update_selected_tags_label()
        
        self.controller.show_frame("MainPageFrame")
        main_frame = self.controller.frames["MainPageFrame"]
        main_frame.refresh_plans()

    
    def show_message(self, message: str, message_type: str = "error") -> None:
    #Display message in results area
    
    #Args: message: Message to display, message_type: 'error', 'success', or 'loading'
    
        icons = {"error": "❌", "success": "✅", "loading": "⏳"}
        colors = {"error": "#ff6b6b", "success": "#4CAF50", "loading": "#cccccc"}
    
        icon = icons.get(message_type, "")
        color = colors.get(message_type, "#cccccc")
    
        self.plan_results_label.configure(text=f"{icon} {message}", text_color=color)
    
    def plan_outing(self) -> None:
    #Execute the outing planning process with user inputs.
    
        #Validate all inputs before proceeding
        if not self.validate_planning_inputs():
            return
    
        #Extract user inputs from form
        max_distance = float(self.distance_entry.get().strip())
        start_time_str = self.start_time.get()
        end_time_str = self.end_time.get()
    
        #Get location name from display for showing in results
        start_location_name = self.start_loc_display.cget("text").replace("📍 ", "")
    
        #Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        self.plan_results_label = ctk.CTkLabel(self.results_frame, text="Preparing your plan...", text_color="#cccccc", font=("Open Sans", 11), wraplength=300)
        self.plan_results_label.pack(pady=20)
    
        #Show loading state
        self.show_message("Planning your perfect outing...\nThis may take a few seconds.", "loading")
    
        #Execute planning in background thread
        planning_thread = threading.Thread(
            target=self.execute_planning,
            daemon=True,
            args=(start_location_name, "", max_distance, start_time_str, end_time_str)
        )
        planning_thread.start()
    
    def on_tag_toggle(self, tag_name):
    #Toggle tag selection and button color
        if tag_name in self.selected_tags:
            self.selected_tags.remove(tag_name)
            self.tag_buttons[tag_name].configure(fg_color="#2a2a2a")
        else:
            self.selected_tags.append(tag_name)
            self.tag_buttons[tag_name].configure(fg_color="#6a1a9b")
        self.update_selected_tags_label()

    def update_selected_tags_label(self):
    #Show selected tags under the buttons.
        if self.selected_tags:
            tags_text = ", ".join(self.selected_tags)
        else:
            tags_text = "None selected"
        self.selected_tags_label.configure(text=f"Selected tags: {tags_text}")
    
    def execute_planning(self, start_location: str, activity_description: str, 
                        max_distance: float, start_time_str: str, end_time_str: str) -> None:
        
        #Execute the planning algorithm in a background thread.
        
        #Args: start_location (str): User's starting location, activity_description (str): Desired activity type, max_distance (float): Maximum travel distance in km, start_time_str (str): Outing start time, end_time_str (str): Outing end time
        
        try:
            #Step 1: Use stored coordinates directly
            self.update_results("🔍 Using your selected location...")
            start_coords = self.start_coords
        
            #Step 2: Convert tags to OSM search tags
            self.update_results("🎯 Analyzing activity preferences...")
            osm_tags = self.get_osm_tags_from_selected()
            
            #Step 3: Search for relevant places
            self.update_results("🗺️ Searching for nearby places...")
            places = self.planner.query_osm_places(start_coords[0], start_coords[1], max_distance, osm_tags)
            
            if not places:
                self.show_message("No places found matching your criteria. Try increasing distance or changing activity type.")
                return
            
            #Step 4: Prepare datetime objects for scheduling
            self.update_results("📅 Creating your itinerary...")
            start_hour, start_minute = map(int, start_time_str.split(':'))
            end_hour, end_minute = map(int, end_time_str.split(':'))

            #Create objects to dictate when the outing starts and ends
            outing_start = datetime(self.selected_date.year, self.selected_date.month, self.selected_date.day, start_hour, start_minute)
        
            outing_end = datetime(self.selected_date.year, self.selected_date.month, self.selected_date.day, end_hour, end_minute)
            
            #Step 5: Generate optimized itinerary
            self.update_results("📅 Creating your perfect itinerary...")
            itinerary = self.planner.create_optimal_itinerary(places, start_coords, outing_start, outing_end)
            
            if not itinerary:
                self.show_message("Couldn't create a feasible itinerary. Try adjusting your criteria.")
                return
            
            #Step 6: Display final plan to user
            self.display_final_plan(itinerary, start_location, len(places))
            
        except Exception as e:
            self.show_message(f"Planning error: {str(e)}")
    
    def update_results(self, message: str) -> None:
        
        #Update results label from background thread.
        
        #Args: message (str): Progress message to display

        self.plan_results_label.configure(text=f"⏳ {message}")
    
    def get_osm_tags_from_selected(self) -> List[str]:
    #Convert selected category tags to OSM search tags
        tag_to_osm = {
            "Outdoors": "leisure=park|natural=wood|natural=beach",
            "Fun": "tourism=attraction|leisure=adult_gaming_centre",
            "Food": "amenity=restaurant|amenity=cafe|amenity=fast_food",
            "Arcade": "leisure=adult_gaming_centre",
            "Family": "leisure=playground|tourism=zoo|tourism=aquarium",
            "Romantic": "tourism=viewpoint|amenity=restaurant",
            "Shopping": "shop=department_store|shop=mall",
            "Culture": "tourism=museum|tourism=gallery|tourism=theatre"
        }
    
        osm_tags = []
        for tag in self.selected_tags:
            if tag in tag_to_osm:
                osm_tags.append(tag_to_osm[tag])
    
        return osm_tags if osm_tags else ["tourism=attraction"]
    
    def save_plan_to_db(self, itinerary, start_location):
    #Save the plan to database linked to the logged-in user
    
        #Check if user is logged in (Absolute safety check)
        if not self.controller.current_user_id:
            self.show_message("❌ Error: No user logged in!", "error")
            return
    
        try:
            with sqlite3.connect("outerinator.db") as conn:
                cursor = conn.cursor()

                #Format itinerary details
                details = "\n".join([
                    f"{i+1}. {item['activity']} ({item['type']}) "
                    f"from {item['start_time'].strftime('%H:%M')} to {item['end_time'].strftime('%H:%M')}"
                    for i, item in enumerate(itinerary)
                ])

                #Generate a nice plan name
                plan_name = f"Outing - {self.selected_date.strftime('%d %B %Y')}"

                #Insert plan with user_id instead of username
                cursor.execute("""
                    INSERT INTO plans (user_id, plan_name, start_location, date, start_time, end_time, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.controller.current_user_id,
                    plan_name,
                    start_location,
                    self.selected_date.strftime("%Y-%m-%d"),
                    self.start_time.get(),
                    self.end_time.get(),
                    details
                ))
                conn.commit()

            #Sow success message in a popup
            self.show_success_popup(plan_name, len(itinerary))

        except Exception as e:
            self.show_message(f"❌ Could not save plan: {e}", "error")
    
    def show_success_popup(self, plan_name, activity_count):
    #Display a popup window when plan is successfully saved
    
        #Create popup window
        popup = ctk.CTkToplevel(self)
        popup.title("Success! 🎉")
        popup.geometry("400x250")
        popup.resizable(False, False)
    
        #Center the popup on screen
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (400 // 2)
        y = (popup.winfo_screenheight() // 2) - (250 // 2)
        popup.geometry(f"400x250+{x}+{y}")
    
        #Make it on top
        popup.transient(self)
        popup.grab_set()
    
        #Configure popup appearance
        popup.configure(fg_color="#d4edda")
    
        #Header
        header_frame = ctk.CTkFrame(popup, fg_color="#4CAF50", corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 20))
    
        header_label = ctk.CTkLabel(header_frame, text="✅ Success!", font=("Open Sans", 18, "bold"), text_color="white")
        header_label.pack(pady=15)
    
        #Message content
        message = (
            f"Your plan has been saved successfully, {self.controller.current_username}!\n\n"
            f"Plan: {plan_name}\n"
            f"Date: {self.selected_date.strftime('%A, %d %B %Y')}\n"
            f"Activities: {activity_count}"
        )

        message_label = ctk.CTkLabel(popup, text=message, font=("Open Sans", 13), text_color="#2b2b2b", wraplength=350, justify="center")
        message_label.pack(pady=(10, 30), padx=20)

        #OK button
        ok_button = ctk.CTkButton(popup, text="OK", command=popup.destroy, fg_color="#4CAF50", hover_color="#45a049", width=120, height=40, font=("Open Sans", 13, "bold"), corner_radius=10)
        ok_button.pack(pady=(0, 20))

        #Focus on the OK button
        ok_button.focus()

        #Allow Enter key to close
        popup.bind('<Return>', lambda e: popup.destroy())
        
    def display_final_plan(self, itinerary: List[Dict], start_location: str, total_places: int) -> None:
    #Display the finalized outing plan in the results area
    
        #Store itinerary for saving later
        self.current_itinerary = itinerary
        self.current_start_location = start_location
    
        #Clear previous results
        if hasattr(self, 'results_frame') and self.results_frame.winfo_exists():
            for widget in self.results_frame.winfo_children():
                try:
                    if widget.winfo_exists():
                        widget.destroy()
                except:
                    pass
    
        #Clear all markers from map
        if hasattr(self, 'map_widget') and self.map_widget.winfo_exists():
            try:
                self.map_widget.clear_all_markers()
            except:
                pass
                
        #Create/recreate the results label
        if hasattr(self, 'results_frame') and self.results_frame.winfo_exists():
            self.plan_results_label = ctk.CTkLabel(self.results_frame, text="", text_color="#cccccc", font=("Open Sans", 11), wraplength=300)
            self.plan_results_label.pack(pady=10)

        #Plan title
        title = ctk.CTkLabel(self.results_frame, text="🎉 Your Perfect Outing Plan! 🎉", text_color="#4CAF50", font=("Open Sans", 16, "bold"))
        title.pack(pady=(10, 5))

        #Plan summary
        activity_count = len(itinerary)
        summary_text = (
            f"Starting from: {start_location}\n"
            f"Found {total_places} places • {activity_count} activities planned\n"
            f"Date: {self.selected_date.strftime('%A, %d %B %Y')}\n"
            f"Time: {self.start_time.get()} - {self.end_time.get()}"
        )

        summary = ctk.CTkLabel(self.results_frame, text=summary_text, text_color="#cccccc", font=("Open Sans", 12))
        summary.pack(pady=(0, 15))

        #Itinerary section header
        itinerary_label = ctk.CTkLabel(self.results_frame, text="📅 Your Itinerary:", text_color="#d78adf", font=("Open Sans", 14, "bold"))
        itinerary_label.pack(anchor="w", pady=(0, 10))

        #Display each itinerary item
        all_coords = []

        for i, item in enumerate(itinerary):
            activity_frame = ctk.CTkFrame(self.results_frame, fg_color="#2a2a2a", corner_radius=6)
            activity_frame.pack(fill="x", pady=3, padx=5)

            #Format times
            start_str = item['start_time'].strftime('%H:%M')
            end_str = item['end_time'].strftime('%H:%M')
            duration_str = f"{item['duration']:.1f}h"
            travel_str = f"{item['travel_time']*60:.0f}min"
            distance_str = f"{item['distance']:.1f}km"

            #Format activity information
            activity_text = (
                f"{i+1}. {item['activity']}\n"
                f"   ⏰ {start_str} - {end_str} ({duration_str})\n"
                f"   🚗 {travel_str} travel ({distance_str})"
            )

            activity_label = ctk.CTkLabel(activity_frame, text=activity_text, text_color="white", font=("Open Sans", 11), justify="left")
            activity_label.pack(padx=10, pady=8, anchor="w")

            #Store coordinates for map
            all_coords.append(item['coordinates'])

        #Update map with markers
        if itinerary:
            #Add start location marker
            start_coords = self.planner.geocode_location(start_location)
            if start_coords:
                self.map_widget.map_widget.set_marker(
                    start_coords[0], 
                    start_coords[1], 
                    text="🚩 Start", 
                    marker_color_circle="#4CAF50", 
                    marker_color_outside="#4CAF50", 
                    text_color="#4CAF50"
                )
                all_coords.insert(0, start_coords)

            #Add activity markers
            for i, item in enumerate(itinerary):
                self.map_widget.map_widget.set_marker(
                    item['coordinates'][0], 
                    item['coordinates'][1], 
                    text=f"{i+1}. {item['activity'][:20]}...", 
                    marker_color_circle="#FF9800", 
                    marker_color_outside="#FF9800"
                )

            #Position map to show all locations
            if len(all_coords) > 1:
                avg_lat = sum(coord[0] for coord in all_coords) / len(all_coords)
                avg_lon = sum(coord[1] for coord in all_coords) / len(all_coords)

                self.map_widget.map_widget.set_position(avg_lat, avg_lon)
                self.map_widget.map_widget.set_zoom(12)

        #Show message if no activities were planned
        if not itinerary:
            no_activities_label = ctk.CTkLabel(self.results_frame, text="No suitable activities found. Try:\n• Increasing the distance\n• Using different search terms\n• Checking if places are open on your selected date", text_color="#ff6b6b",  font=("Open Sans", 11), justify="center")
            no_activities_label.pack(pady=20)

        #Save button at the bottom of results
        if itinerary:
            save_button = ctk.CTkButton(self.results_frame, text="💾 Save This Plan", command=lambda: self.save_plan_to_db(self.current_itinerary, self.current_start_location), fg_color="#4CAF50", hover_color="#45a049", height=40, font=("Open Sans", 13, "bold"), corner_radius=10)
            save_button.pack(pady=(20, 10), padx=20, fill="x")
            
    def __init__(self, parent, controller):
        #Initialise the planning frame with all planning components.
        
        #Args: parent: Parent widget, controller: Main application controller
        
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=main_colour_theme)
        self.planner = OutingPlanner()  #Core planning functions
        
        #Main grid configuration
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) 
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=1) 
        
        #Store all tags/interests the user selects
        self.selected_tags = []

        #Page title
        self.page_label = ctk.CTkLabel(self, text="Plan your outing!", text_color="#d78adf", fg_color="#000000", corner_radius=5, font=("Open Sans", 24))
        self.page_label.grid(row=0, column=0, columnspan=2, pady=20)
    
        #Left side (Planning form and controls)
        left_side = ctk.CTkScrollableFrame(self, fg_color="transparent", height=520)
        left_side.grid(row=1, column=0, sticky="nsew", pady=8, padx=10)

        #Configure grid
        for i in range(10):
            left_side.grid_rowconfigure(i, weight=0)
        left_side.grid_rowconfigure(9, weight=1)
        left_side.grid_columnconfigure(0, weight=1)

        #Starting location
        start_loc_frame = ctk.CTkFrame(left_side, fg_color="transparent")
        start_loc_frame.grid(row=0, column=0, pady=(0, 10), padx=5, sticky="ew")
        start_loc_frame.grid_columnconfigure(0, weight=1)

        self.start_loc_label = ctk.CTkLabel(start_loc_frame, text="Starting from:", text_color="#d78adf", font=("Open Sans", 12))
        self.start_loc_label.grid(row=0, column=0, sticky="w")

        #Info label
        info_label = ctk.CTkLabel(start_loc_frame, text="👉 Use the map on the right to search and select your location (Search up an address and it will be added as your starting location! If you input the wrong location, just type out another address.)", text_color="#aaaaaa", font=("Open Sans", 10), wraplength=300, justify="left")
        info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        #Display selected location (read-only)
        self.start_loc_display = ctk.CTkLabel(start_loc_frame, text="📍 No location selected", text_color="#4CAF50", font=("Open Sans", 11, "bold"), anchor="w", wraplength=300, justify="left")
        self.start_loc_display.grid(row=2, column=0, sticky="w", pady=(5, 0))

        #Store coordinates
        self.start_coords = None

        #Category selection
        category_label = ctk.CTkLabel(left_side, text="Categories:", text_color="#d78adf", font=("Open Sans", 12))
        category_label.grid(row=2, column=0, pady=(5, 5), padx=5, sticky="w")

        self.category_frame = ctk.CTkFrame(left_side, fg_color="transparent")
        self.category_frame.grid(row=3, column=0, pady=(0, 15), padx=5, sticky="ew")

        #Store tag references for toggling
        self.tag_buttons = {}

        categories = [
            [("🌳 Outdoors", "Outdoors"), ("🎯 Fun", "Fun"), ("🍕 Food", "Food"), ("🎮 Arcade", "Arcade")],
            [("👨‍👩‍👧‍👦 Family", "Family"), ("💝 Romantic", "Romantic"),
             ("🛍️ Shopping", "Shopping"), ("🏛️ Culture", "Culture")]
        ]

        for row_idx, row_categories in enumerate(categories):
            row_frame = ctk.CTkFrame(self.category_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            for text, tag_name in row_categories:
                btn = ctk.CTkButton(row_frame, text=text, width=85, height=30, fg_color="#2a2a2a", hover_color="#444444", command=lambda t=tag_name: self.on_tag_toggle(t))
                btn.pack(side="left", padx=2)
                self.tag_buttons[tag_name] = btn
                
        #Label to show current selections
        self.selected_tags_label = ctk.CTkLabel(left_side, text="Selected tags: None selected", wraplength=250, anchor="w", justify="left")
        self.selected_tags_label.grid(row=4, column=0, padx=5, pady=(5, 10), sticky="w")

        #Max travel distance (moved down to new row)
        distance_frame = ctk.CTkFrame(left_side, fg_color="transparent")
        distance_frame.grid(row=5, column=0, pady=(10, 5), padx=5, sticky="ew")
        distance_frame.columnconfigure(0, weight=1)

        self.distance_label = ctk.CTkLabel(distance_frame, text="Max travel distance (km):", text_color="#d78adf", font=("Open Sans", 12))
        self.distance_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.distance_entry = ctk.CTkEntry(distance_frame, width=120, height=32, placeholder_text="e.g., 10")
        self.distance_entry.grid(row=1, column=0, sticky="w")
        self.distance_entry.insert(0, "10")

        #Time selection
        time_frame = ctk.CTkFrame(left_side, fg_color="transparent")
        time_frame.grid(row=6, column=0, pady=10, padx=5, sticky="ew")

        self.time_label = ctk.CTkLabel(time_frame, text="What time?", text_color="#d78adf", font=("Open Sans", 12))
        self.time_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        time_selection_frame = ctk.CTkFrame(time_frame, fg_color="transparent")
        time_selection_frame.grid(row=1, column=0, sticky="ew")

        start_times = [f"{h:02d}:00" for h in range(6, 24)] + [f"{h:02d}:30" for h in range(6, 24)]
        self.start_time = ctk.CTkOptionMenu(time_selection_frame, values=start_times, width=90)
        self.start_time.pack(side="left", padx=(0, 5))
        self.start_time.set("10:00")

        ctk.CTkLabel(time_selection_frame, text="to").pack(side="left", padx=5)

        end_times = [f"{h:02d}:00" for h in range(7, 24)] + [f"{h:02d}:30" for h in range(7, 24)] + ["23:59"]
        self.end_time = ctk.CTkOptionMenu(time_selection_frame, values=end_times, width=90)
        self.end_time.pack(side="left", padx=(5, 0))
        self.end_time.set("18:00")

        #Date selection
        date_frame = ctk.CTkFrame(left_side, fg_color="transparent")
        date_frame.grid(row=7, column=0, pady=10, padx=5, sticky="ew")
        date_frame.columnconfigure(0, weight=1)
        date_frame.columnconfigure(1, weight=1)
        date_frame.columnconfigure(2, weight=1)

        self.date_label = ctk.CTkLabel(date_frame, text="Which date?", text_color="#d78adf", font=("Open Sans", 12))
        self.date_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

        #Date initialisation
        today = date.today()
        current_year = today.year
        current_month = today.month
        current_day = today.day

        years = [str(y) for y in range(current_year, current_year + 3)]
        months = [str(m).zfill(2) for m in range(1, 13)]
        days = [str(d).zfill(2) for d in range(1, 32)]

        #Create variables with today's date
        self.year_var = ctk.StringVar(value=str(current_year))
        self.month_var = ctk.StringVar(value=str(current_month).zfill(2))
        self.day_var = ctk.StringVar(value=str(current_day).zfill(2))

        #Create dropdown menus
        self.year_menu = ctk.CTkOptionMenu(date_frame, values=years, variable=self.year_var, width=90)
        self.year_menu.grid(row=1, column=0, padx=3, sticky="ew")

        self.month_menu = ctk.CTkOptionMenu(date_frame, values=months, variable=self.month_var, width=80)
        self.month_menu.grid(row=1, column=1, padx=3, sticky="ew")

        self.day_menu = ctk.CTkOptionMenu(date_frame, values=days, variable=self.day_var, width=80)
        self.day_menu.grid(row=1, column=2, padx=3, sticky="ew")

        #Initialise selected_date to today's date
        self.selected_date = today

        #Date preview label
        self.date_display = ctk.CTkLabel(date_frame, text=today.strftime("%Y/%m/%d"), text_color="#aaaaaa", font=("Open Sans", 11))
        self.date_display.grid(row=2, column=0, columnspan=3, pady=(8, 0))

        #Automatically update the preview when any dropdown changes
        update_date_display = lambda *args: (self.date_display.configure(text=f"{self.year_var.get()}-{self.month_var.get()}-{self.day_var.get()}"), setattr(self, "selected_date", date(int(self.year_var.get()), int(self.month_var.get()), int(self.day_var.get()))))

        self.year_var.trace_add("write", update_date_display)
        self.month_var.trace_add("write", update_date_display)
        self.day_var.trace_add("write", update_date_display)
        
        #Plan button
        self.search_button = ctk.CTkButton(left_side, text="✨ Plan My Outing!", command=self.plan_outing, fg_color="#007acc", hover_color="#005a99", height=42, font=("Open Sans", 14, "bold"), corner_radius=12)
        self.search_button.grid(row=8, column=0, pady=(20, 10), sticky="ew", padx=5)

        #Results area
        self.results_frame = ctk.CTkScrollableFrame(left_side, fg_color="#1a1a1a", corner_radius=8, height=200)
        self.results_frame.grid(row=9, column=0, sticky="nsew", pady=10)
        self.results_frame.grid_columnconfigure(0, weight=1)

        self.plan_results_label = ctk.CTkLabel(self.results_frame, text="Fill in your outing details above and click 'Plan My Outing!'", text_color="#cccccc", font=("Open Sans", 11), wraplength=300)
        self.plan_results_label.pack(pady=20)
        
        #Right side (Map display)
        right_side = ctk.CTkFrame(self, fg_color="transparent")
        right_side.grid(row=1, column=1, sticky="nsew", pady=5, padx=5)
        right_side.grid_rowconfigure(0, weight=1)
        right_side.grid_columnconfigure(0, weight=1)
        
        #Map widget for visualizing outing locations
        self.map_widget = MapWidget(right_side, width=400, height=400)
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        
        #Connect map location selection to planning frame
        self.map_widget.set_location_callback(self.set_start_location_from_map)
        
        #Navigation back to main page
        back_button = ctk.CTkButton(self, text="⬅ Back to Main", command=lambda: self.return_to_main(), fg_color="#cc0000", hover_color="#990000", corner_radius=12, height=38)
        back_button.grid(row=2, column=0, columnspan=2, pady=(8, 20), padx=10, sticky="ew")

app = Outerinator()
app.mainloop()