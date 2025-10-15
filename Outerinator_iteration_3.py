import sqlite3
import re
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import customtkinter as ctk
import tkintermapview
import threading
import time
from PIL import Image
import os
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError

class Outerinator(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Outerinator")
        self.geometry("600x400")
        
        #Create a container to hold all frames
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        
        #Create instances of each frame (Making sure that the frames exist)
        for F in (OpeningFrame, SigninFrame, SignUpFrame, MainPageFrame):
            frame_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        #Show the initial frame
        self.show_frame("OpeningFrame")
        
        self.mainloop()
    
    def show_frame(self, frame_name):
        #Switching between frames when button is pressed
        frame = self.frames[frame_name]
        frame.tkraise()

class OpeningFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        #Configuring the frame background color
        self.configure(fg_color="#00199c")
        
        #Configure frame rows and columns
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(2, weight=2)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
            
        #Creating components
        label = ctk.CTkLabel(self, text="Welcome to Outerinator", text_color="#d78adf", font=("Open Sans", 30))
        label.grid(row = 0, column = 0, pady=20, padx=10, columnspan=2, sticky = "ew")
        
        try:
            #Finding the logo image path
            script_directory = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_directory, "Outerinator_Logo.png")
            
            
            self.logo_image = ctk.CTkImage(Image.open(logo_path), size=(200, 200))
            image_label = ctk.CTkLabel(self, image=self.logo_image, text="")
            image_label.grid(row=1, column=0, columnspan=2, pady=20)
        except Exception as e:
            image_placeholder = ctk.CTkLabel(self, text="Logo Image Not Found", font=("Arial", 16), fg_color="#ff0000")
            image_placeholder.grid(row=1, column=0, columnspan=2, pady=20)
        
        SignIn_button = ctk.CTkButton(self, text="SignIn", command=lambda: controller.show_frame("SigninFrame"), fg_color="#007acc", hover_color="#005a99")
        SignIn_button.grid(row=2, column=0, pady=20, padx=10, sticky="ew")
        
        signup_button = ctk.CTkButton(self, text="Sign Up", command= lambda: controller.show_frame("SignUpFrame"), fg_color="#00cc00", hover_color="#009900")
        signup_button.grid(row=2, column=1, pady=20, padx=10, sticky="ew")

class SigninFrame(ctk.CTkFrame):
    def SignIn(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        connection = sqlite3.connect('outerinator.db', timeout=10)
        cursor = connection.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user_verify = cursor.fetchone()
        
        if username == "":
            #Checks that username field is not empty
            self.error_label.configure(state="normal")
            self.error_label.delete("1.0", tk.END)
            self.error_label.insert("1.0", "Please enter username")
            self.error_label.configure(state="disabled")
            connection.close()
            
        elif user_verify and user_verify[0] == password:
            #Checks if the password matches with the username
            self.error_label.configure(state="normal")
            self.error_label.delete("1.0", tk.END)
            self.error_label.insert("1.0", "SignIn successful!")
            self.error_label.configure(state="disabled")
            self.error_label.after(1000, lambda: self.controller.show_frame("MainPageFrame"))
            connection.close()
            return
        
        elif user_verify:
            #Returns a false if the password is wrong
            self.error_label.configure(state="normal")
            self.error_label.delete("1.0", tk.END)
            self.error_label.insert("1.0", "Incorrect password.")
            self.error_label.configure(state="disabled")
            connection.close()
            return
        
        else:
            #Returns a false if the username is not found
            self.error_label.configure(state="normal")
            self.error_label.delete("1.0", tk.END)
            self.error_label.insert("1.0", "Username not found.")
            self.error_label.configure(state="disabled")
            connection.close()
            return
        
    def toggle_password(self):
    #Code to control the visibility of the password
        if self.show_password:
            self.password_entry.configure(show="*")
            self.eye_image.configure(text="👁️")
            self.show_password = False
        else:
            self.password_entry.configure(show="")
            self.show_password = True
            
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        #Configuring the frame background color
        self.configure(fg_color="#00199c")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        #Create widgets
        label = ctk.CTkLabel(self, text="Sign In", text_color="#d78adf", font=("Arial", 24))
        label.grid(row=0, column=0, columnspan=2, pady=20)
        
        #Username label and entry
        username_label = ctk.CTkLabel(self, text="Username:", text_color="#d78adf")
        username_label.grid(row=1, column=0, pady=5)
        
        self.username_entry = ctk.CTkEntry(self, width=200)
        self.username_entry.grid(row=2, column=0, pady=5)
        
        #Password label and entry
        password_label = ctk.CTkLabel(self, text="Password:", text_color="#d78adf")
        password_label.grid(row=3, column=0, pady=5)
        
        self.password_entry = ctk.CTkEntry(self, show="*", width=200)
        self.password_entry.grid(row=4, column=0, pady=5)
        
        self.show_password = False
        self.eye_image = ctk.CTkButton(self, text="👁️", text_color="#318ccd", width=10, height=5, fg_color="transparent", bg_color="#f9f9fa", command= self.toggle_password)
        self.eye_image.place(in_=self.password_entry, relx=1.0, x=-5, rely=0.5, anchor="e")
        
        #Error label
        self.error_label = ctk.CTkTextbox(self, wrap="word", height=50, width=200, state="disabled", fg_color="#00199c", text_color="#ff0000")
        self.error_label.grid(row=2, column=1, pady=5)
        
        #SignIn button
        SignIn_button = ctk.CTkButton(self, text="SignIn", 
                                   command=self.SignIn,
                                   fg_color="#007acc", hover_color="#005a99")
        SignIn_button.grid(row=5, column=0, pady=20, padx=10, sticky="ew")
        
        #Back button
        back_button = ctk.CTkButton(self, text="Back", 
                                  command=lambda: controller.show_frame("OpeningFrame"),
                                  fg_color="#cc0000", hover_color="#990000")
        back_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")

class SignUpFrame(ctk.CTkFrame):
    def toggle_password(self):
        #Code to control the visibility of the password
        if self.show_password:
            self.new_password_entry.configure(show="*")
            self.eye_image.configure(text="👁️")
            self.show_password = False
        else:
            self.new_password_entry.configure(show="")
            self.show_password = True
            
    def signup(self):
        #Obtaining the username and password that the user entered
        username = self.new_username_entry.get()
        password = self.new_password_entry.get()

        #Validating the password based on elements that a strong password should have
        connection = sqlite3.connect('outerinator.db', timeout=10)
        cursor = connection.cursor()
        if password == "":
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Please enter a password")
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if len(password) <= 8:
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must be more than 8 characters")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if not re.search("[a-z]", password):
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must contain at least one lowercase letter")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if not re.search("[A-Z]", password):
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must contain at least one uppercase letter")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if not re.search("[0-9]", password):
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must contain at least one number")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if not re.search("[_@!$?]", password):
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must contain at least one special character (_@!$?)")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        if re.search("\s", password):
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password must not contain spaces")
            self.new_password_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return
        
        #Checks if the username is already taken
        existing_user = cursor.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
    
        if existing_user:
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Username already exists. Please choose another.")
            self.new_password_entry.delete(0, tk.END)
            self.new_username_entry.delete(0, tk.END)
            self.result_label.configure(state="disabled")
            connection.close()
            return

        #Saving the information to the database given all the criteria are met
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
            connection.commit()
            self.result_label.configure(state="normal")
            self.result_label.delete("1.0", tk.END)
            self.result_label.insert("1.0", "Password is valid and user saved! Please return to the Sign In tab.")
            self.new_password_entry.delete(0, tk.END)
            self.new_username_entry.delete(0, tk.END)
        finally:
            connection.close()
            
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        #Configuring frame background color
        self.configure(fg_color="#318ccd")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        #Creating components
        label = ctk.CTkLabel(self, text="Sign Up", text_color="#8c009c", font=("Arial", 24))
        label.grid(row=0, column=0, columnspan=2, pady=20, sticky="ew")
        
        #Username label and entry
        new_username_label = ctk.CTkLabel(self, text="Choose a Username:", text_color="#8c009c")
        new_username_label.grid(row=1, column=0, pady=5, sticky="nsew")
        self.new_username_entry = ctk.CTkEntry(self, width=200)
        self.new_username_entry.grid(row=2, column=0, pady=5)
        
        #Password label
        new_password_label = ctk.CTkLabel(self, text="Choose a Password:", text_color="#8c009c")
        new_password_label.grid(row=3, column=0, pady=5, sticky="nsew")
        
        #Password entry
        self.new_password_entry = ctk.CTkEntry(self, show="*", width=200)
        self.new_password_entry.grid(row=4, column=0, pady=5)
        
        #Eye button to show/hide password
        self.show_password = False
        self.eye_image = ctk.CTkButton(self, text="👁️", text_color="#8c009c", width=10, height=5, fg_color="transparent", bg_color="#f9f9fa", command= self.toggle_password)
        self.eye_image.place(in_=self.new_password_entry, relx=1.0, x=-5, rely=0.5, anchor="e")
        
        #Result label
        self.result_label = ctk.CTkTextbox(self, wrap="word", height=50, width=200, state="disabled", fg_color="#318ccd", text_color="#ff0000")
        self.result_label.grid(row=2, column=1, pady=10, sticky="nsew")
        
        #Sign Up button
        signup_button = ctk.CTkButton(self, text="Sign Up", command=self.signup, fg_color="#00cc00", hover_color="#009900")
        signup_button.grid(row=5, column=0, pady=20, padx=10, sticky="ew")
        
        #Back button
        back_button = ctk.CTkButton(self, text="Back", command=lambda: controller.show_frame("OpeningFrame"), fg_color="#cc0000", hover_color="#990000")
        back_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")

class MainPageFrame(ctk.CTkFrame):
    def setup_map_controls(self):
        #Making sure the map can fit in the program window when it is small
        controls_frame = ctk.CTkFrame(self.map_container, fg_color="transparent", height=30)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        controls_frame.grid_propagate(False)
        controls_frame.columnconfigure(0, weight=1)
        
        #Search frame
        search_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="w")
        
        #Search entry
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search...", width=120, height=25)
        self.search_entry.pack(side="left", padx=(0, 3))
        
        #Search button
        self.search_btn = ctk.CTkButton(search_frame, text="🔍", command=self.robust_search_location, width=30, height=25)
        self.search_btn.pack(side="left", padx=(0, 5))
        
        #Clear results button
        clear_results_btn = ctk.CTkButton(search_frame, text="❌", command=self.clear_address_results, width=25, height=25, fg_color="transparent", hover_color="#333333")
        clear_results_btn.pack(side="left", padx=(0, 5))
        
        #Buttons to interact with the map
        action_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")
        
        #Buttons with icons
        add_marker_btn = ctk.CTkButton(action_frame, text="📍", command=self.add_marker_at_center, width=30, height=25)
        add_marker_btn.pack(side="left", padx=2)
        
        clear_markers_btn = ctk.CTkButton(action_frame, text="🗑️", command=self.clear_all_markers, width=30, height=25)
        clear_markers_btn.pack(side="left", padx=2)
        
        #Label to display errors - FIXED: Make it an instance variable
        self.map_error_label = ctk.CTkLabel(action_frame, text="", text_color="red", font=("Arial", 10))
        self.map_error_label.pack(side="left", padx=5)   
        
    def setup_geocoder(self):
        #Sets up the geocoder by a user agent (which allows us to use web content which in this case is the map)
        try:
            self.geolocator = Nominatim(user_agent="outerinator_app/1.0 (your_email@example.com)")
        except:
            self.geolocator = None

    def robust_search_location(self):
        #Using our own search function to bypass tkintermapview's search
        query = self.search_entry.get().strip()
        if not query:
            return
        
        self.search_btn.configure(state="disabled", text="Searching...")
        
        #Clear previous results
        self.clear_address_results()
        
        #Using a thread to make the program run smoothly
        threading.Thread(target=self.search_thread_target, args=(query,), daemon=True).start()

    def search_thread_target(self, query):
        #Thread to search smoothly
        try:
            #Making sure that we don't make too many requests too quickly, resulting in error 403 again
            time.sleep(1)
            
            #Get ALL location results (no limit)
            results = self.get_all_locations(query)
            
            #Update UI in main thread
            if results:
                self.after(0, lambda: self.show_address_results(results))
            else:
                self.after(0, self.on_search_error)
                
        except Exception as e:
            self.after(0, lambda: self.on_search_error(str(e)))

    def get_all_locations(self, query):
        #Get all location results from OSM
        headers = {'User-Agent': 'OuterinatorApp/1.0 (https://myapp.com)', 'Accept': 'application/json', 'Referer': 'https://myapp.com'}
    
        try:
            #Get ALL results
            response = requests.get("https://nominatim.openstreetmap.org/search", params={'q': query, 'format': 'json', 'addressdetails': 1}, headers=headers, timeout=10)
        
            if response.status_code == 200:
                data = response.json()
                
                if data:
                    return data
                else:
                    return None
                
            else:
                self.after(0, lambda: self.map_error_label.configure(text=f"API returned status: {response.status_code}"))
                self.after(0, self.clear_error_after_delay)
                return None
            
        except Exception as e:
            self.after(0, lambda: self.map_error_label.configure(text=f"Search error: {e}"))
            self.after(0, self.clear_error_after_delay)
            return None
        
    def clear_error_after_delay(self):
        #Clear the error label after 3 seconds
        self.after(3000, lambda: self.map_error_label.configure(text=""))
        
    def show_address_results(self, results):
        #Display ALL address results in a scrollable frame
        self.search_btn.configure(state="normal", text="Search")
    
        #Create scrollable results frame if it doesn't exist
        if not hasattr(self, 'results_frame'):
            self.results_frame = ctk.CTkFrame(self.map_container, fg_color="#1a1a1a", corner_radius=6)
            self.results_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
            self.results_frame.grid_rowconfigure(0, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)

            #Create scrollable frame inside results frame
            self.scrollable_frame = ctk.CTkScrollableFrame(self.results_frame, fg_color="#1a1a1a", height=150)
            self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
    
        #Make sure the frame is visible and properly configured
        self.results_frame.grid()
    
        #Clear previous results PROPERLY - destroy all children
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
        #Show how many results were found
        results_count = len(results)
        title_text = f"Found {results_count} locations (showing all):"
    
        title_label = ctk.CTkLabel(self.scrollable_frame, text=title_text, font=("Arial", 12, "bold"), text_color="white")
        title_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 10))
    
        #Add each result as a clickable button
        for i, result in enumerate(results):
            #Create display name from address components
            display_name = self.format_display_name(result)
        
            #Create clickable result button
            result_btn = ctk.CTkButton(self.scrollable_frame, text=display_name, command=lambda r=result: self.select_address(r), fg_color="#2a2a2a", hover_color="#3a3a3a", text_color="white", anchor="w", height=30)
            result_btn.grid(row=i+1, column=0, sticky="ew", padx=5, pady=2)
        
            #Add a small label showing the country/region
            country = result.get('display_name', '').split(',')[-1].strip()
            country_label = ctk.CTkLabel(self.scrollable_frame, text=country, font=("Arial", 9), text_color="#cccccc")
            country_label.grid(row=i+1, column=1, sticky="e", padx=(0, 5), pady=2)

    def format_display_name(self, result):
        #Format a readable display name from the result
        address = result.get('display_name', 'Unknown Location')
        
        #Shorten very long names but keep more info
        if len(address) > 80:
            parts = address.split(',')
            if len(parts) >= 4:
                #Show first 4 parts for better context
                address = ', '.join(parts[:4])
            else:
                address = address[:80] + "..."
        
        return address

    def select_address(self, result):
        #User selected an address from the results
        lat = float(result['lat'])
        lon = float(result['lon'])
        display_name = self.format_display_name(result)
        
        #Update map position
        self.update_map_position(lat, lon, display_name)
        
        #Clear results frame
        self.clear_address_results()

    def clear_address_results(self):
    #Clear the address results display
        if hasattr(self, 'results_frame'):
            if hasattr(self, 'scrollable_frame'):
                for widget in self.scrollable_frame.winfo_children():
                    widget.destroy()
            self.results_frame.grid_forget()

    def update_map_position(self, lat, lon, query):
        #Updating the map position and adding a marker to the searched location
        try:
            #Set map position directly to where we want
            self.map_widget.set_position(lat, lon)

            #Add marker at the location
            self.map_widget.set_marker(lat, lon, text=query)

            #Clear search entry
            self.search_entry.delete(0, "end")
        
        except Exception as e:
            self.map_error_label.configure(text=f"Map update error: {e}")
            self.clear_error_after_delay() 

    def on_search_success(self):
        #Triggers when search is successful
        self.search_btn.configure(state="normal", text="Search")
        self.search_entry.delete(0, "end")

    def on_search_error(self, message="Location not found"):
        #Triggers when search fails
        self.search_btn.configure(state="normal", text="Search")
        self.map_error_label.configure(text=f"Search error: {message}")
    
        #Clear error after 3 seconds
        self.clear_error_after_delay()
    
        #Show error in results frame
        if not hasattr(self, 'results_frame'):
            self.results_frame = ctk.CTkFrame(self.map_container, fg_color="#1a1a1a", corner_radius=6)
            self.results_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
            self.results_frame.grid_rowconfigure(0, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)
        
            self.scrollable_frame = ctk.CTkScrollableFrame(self.results_frame, fg_color="#1a1a1a", height=150)
            self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        error_label = ctk.CTkLabel(self.scrollable_frame, text="No locations found. Try a more specific search.", text_color="#ff6b6b", font=("Arial", 11))
        error_label.pack(pady=10)

    def setup_map(self):
        #Initialising the map widget
        try:
            #Creating the map widget
            self.map_widget = tkintermapview.TkinterMapView(self.map_container, width=400, height=250, corner_radius=8)
            self.map_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            
            #Set initial position (Auckland)
            self.map_widget.set_position(-36.8509, 174.7645)
            self.map_widget.set_zoom(12)
            
            #Set tile server
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
            
            #Add initial marker
            self.map_widget.set_marker(-36.8509, 174.7645, text="Auckland City")
            
        except Exception as e:
            self.map_error_label.configure(text=f"Map failed to load: {str(e)}")
        
    def add_marker_at_center(self):
        #Adding a marker in the middle of the map's current location
        position = self.map_widget.get_position()
        marker_text = f"Marker {len(self.map_widget.canvas_marker_list) + 1}"
        self.map_widget.set_marker(position[0], position[1], text=marker_text)

    def clear_all_markers(self):
        #Clearing all markers from the map
        for marker in self.map_widget.canvas_marker_list:
            marker.delete()
            
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color="#00199c")
        
        #Initialising the geocoder
        self.setup_geocoder()
        
        #Main page row and column configuration
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        
        #Left column
        left_column = ctk.CTkFrame(self, fg_color="transparent", width=180)
        left_column.grid(row=0, column=0, rowspan=2, sticky="nswe", padx=(5, 3), pady=5)
        left_column.grid_propagate(False)
        left_column.rowconfigure(0, weight=1)
        left_column.rowconfigure(1, weight=1)
        left_column.columnconfigure(0, weight=1)
        
        #Calendar widget
        self.calendar = ctk.CTkFrame(left_column, fg_color="#3a4044", corner_radius=6, border_width=1, border_color="#000000")
        self.calendar.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        calendar_label = ctk.CTkLabel(self.calendar, text="Calendar", font=("Arial", 12, "bold"), text_color="white")
        calendar_label.pack(pady=8)
        
        #Plans widget
        self.plans = ctk.CTkFrame(left_column, fg_color="#3eaef9", corner_radius=6, border_width=1, border_color="#000000")
        self.plans.grid(row=1, column=0, sticky="nsew", pady=(3, 0))
        plans_label = ctk.CTkLabel(self.plans, text="Plans", font=("Arial", 12, "bold"), text_color="white")
        plans_label.pack(pady=8)
        
        #Right column
        right_column = ctk.CTkFrame(self, fg_color="transparent")
        right_column.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=3, pady=5)
        right_column.rowconfigure(0, weight=0)
        right_column.rowconfigure(1, weight=1)
        right_column.columnconfigure(0, weight=1)
        
        #Banner
        self.banner = ctk.CTkFrame(right_column, fg_color="#3eaef9", corner_radius=6, border_width=1, border_color="#000000", height=50)
        self.banner.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        self.banner.grid_propagate(False)
        
        planning_button = ctk.CTkButton(self.banner, text="Plan an outing", font=("Arial", 12), text_color="white", width=80, height=30)
        planning_button.pack(pady=8, side="left", padx=10)
        
        #Map Container
        self.map_container = ctk.CTkFrame(right_column, fg_color="#2a2a2a", corner_radius=6, border_width=1, border_color="#000000")
        self.map_container.grid(row=1, column=0, sticky="nsew")
        self.map_container.grid_rowconfigure(0, weight=1)
        self.map_container.grid_rowconfigure(1, weight=0)
        self.map_container.grid_rowconfigure(2, weight=1) 
        self.map_container.grid_columnconfigure(0, weight=1)
        
        #Initialise the map
        self.setup_map()
        
        #Add map controls
        self.setup_map_controls()

if __name__ == "__main__":
    app = Outerinator()