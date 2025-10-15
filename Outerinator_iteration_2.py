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
        self.configure(fg_color="#8c009c")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        #Creating components
        label = ctk.CTkLabel(self, text="Sign Up", text_color="#318ccd", font=("Arial", 24))
        label.grid(row=0, column=0, columnspan=2, pady=20, sticky="ew")
        
        #Username label and entry
        new_username_label = ctk.CTkLabel(self, text="Choose a Username:", text_color="#318ccd")
        new_username_label.grid(row=1, column=0, pady=5, sticky="nsew")
        self.new_username_entry = ctk.CTkEntry(self, width=200)
        self.new_username_entry.grid(row=2, column=0, pady=5)
        
        #Password label
        new_password_label = ctk.CTkLabel(self, text="Choose a Password:", text_color="#318ccd")
        new_password_label.grid(row=3, column=0, pady=5, sticky="nsew")
        
        #Password entry
        self.new_password_entry = ctk.CTkEntry(self, show="*", width=200)
        self.new_password_entry.grid(row=4, column=0, pady=5)
        
        #Eye button to show/hide password
        self.show_password = False
        self.eye_image = ctk.CTkButton(self, text="👁️", text_color="#318ccd", width=10, height=5, fg_color="transparent", bg_color="#f9f9fa", command= self.toggle_password)
        self.eye_image.place(in_=self.new_password_entry, relx=1.0, x=-5, rely=0.5, anchor="e")
        
        #Result label
        self.result_label = ctk.CTkTextbox(self, wrap="word", height=50, width=200, state="disabled", fg_color="#8c009c", text_color="#ff0000")
        self.result_label.grid(row=2, column=1, pady=10, sticky="nsew")
        
        #Sign Up button
        signup_button = ctk.CTkButton(self, text="Sign Up", 
                                   command=self.signup,
                                   fg_color="#00cc00", hover_color="#009900")
        signup_button.grid(row=5, column=0, pady=20, padx=10, sticky="ew")
        
        #Back button
        back_button = ctk.CTkButton(self, text="Back", 
                                  command=lambda: controller.show_frame("OpeningFrame"),
                                  fg_color="#cc0000", hover_color="#990000")
        back_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")


class MainPageFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color="#00199c")
        
        #Main page row configuration
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=1)
        
        #Main page column configuration
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        
        #Code for left column content
        left_column = ctk.CTkFrame(self, fg_color="transparent", width=280)
        left_column.grid(row=0, column=0, rowspan=2, sticky="nswe", padx=(10, 5), pady=10)
        left_column.grid_propagate(False)
        
        #COnfiguring rows and columns for the left column
        left_column.rowconfigure(0, weight=1)
        left_column.rowconfigure(1, weight=1)
        left_column.columnconfigure(0, weight=1)
        
        #Calendar widget
        self.calendar = ctk.CTkFrame(left_column, fg_color="#3a4044", corner_radius=8,
                                   border_width=2, border_color="#000000")
        self.calendar.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        calendar_label = ctk.CTkLabel(self.calendar, text="Calendar", 
                                    font=("Arial", 16, "bold"), text_color="white")
        calendar_label.pack(pady=15)
        
        #Plans widget
        self.plans = ctk.CTkFrame(left_column, fg_color="#3eaef9", corner_radius=8,
                                border_width=2, border_color="#000000")
        self.plans.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        
        plans_label = ctk.CTkLabel(self.plans, text="Plans", 
                                 font=("Arial", 16, "bold"), text_color="white")
        plans_label.pack(pady=15)
        
        #Banner confguration
        right_column = ctk.CTkFrame(self, fg_color="transparent")
        right_column.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=10)
        right_column.rowconfigure(0, weight=0)
        right_column.rowconfigure(1, weight=1)
        right_column.columnconfigure(0, weight=1)
        
        #Banner code
        self.banner = ctk.CTkFrame(right_column, fg_color="#3eaef9", corner_radius=8,
                                 border_width=2, border_color="#000000", height=70)
        self.banner.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self.banner.grid_propagate(False)
        
        #Planning button
        planning_button = ctk.CTkButton(self.banner, text="Plan your outing", font=("Arial", 14), text_color="white")
        planning_button.pack(pady=15, side="left", padx=20)
        
        #Map Container
        self.map_container = ctk.CTkFrame(right_column, fg_color="#2a2a2a", corner_radius=8,
                                        border_width=2, border_color="#000000")
        self.map_container.grid(row=1, column=0, sticky="nsew")
        
        #Making a placeholder for the map as it will be included in the next iteration
        map_placeholder = ctk.CTkLabel(self.map_container, text="MAP CONTAINER\n\nThis is where my map will be integrated", 
                                     font=("Arial", 16), text_color="white",
                                     fg_color="#1a1a1a", corner_radius=6, wraplength=100)
        map_placeholder.pack(expand=True, fill="both", padx=20, pady=20)

#Running the application
if __name__ == "__main__":
    app = Outerinator()