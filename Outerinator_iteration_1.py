import sqlite3
import re
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import customtkinter as ctk
import threading
import time

#Making the main window
outerinator = ctk.CTk()
outerinator.title("Outerinator")
outerinator.geometry("600x400")
outerinator.configure(bg="#00ffd9")

#Initialising a notebook so that I can have multiple tabs
notebook = ttk.Notebook(outerinator)
notebook.pack(pady=10, expand=True)

#Attempt to use a different font
opensans_font = tkFont.Font(family="Open Sans")

#Creating and adding the tabs to the notebook
signin_frame = ttk.Frame(notebook, width=600, height=400)
signup_frame = ttk.Frame(notebook, width=600, height=400)
general_frame = ttk.Frame(notebook, width=600, height=400)
chat_frame = ttk.Frame(notebook, width=600, height=400)

notebook.add(signin_frame, text="Sign In")
notebook.add(signup_frame, text="Sign Up")
notebook.add(general_frame, text="General")
notebook.add(chat_frame, text="Chat")
notebook.pack(expand=True, fill='both')

#Making a parent class for later use
class UserInformation():
    def __init__(self, username, password): 
        self.username = username
        self.password = password
    
#Making a class to save the password to the database
class PasswordValidator(UserInformation):
    def __init__(self, username, password):
        super().__init__(username, password)
        
    def is_valid(username, password):
        #Connecting to the database
        connection = sqlite3.connect('outerinator.db')
        cursor = connection.cursor()
        
        #Password validation
        if password == "":
            password_result_label.config(text="Please enter a password")
            return
        if len(password) <= 8:
            password_result_label.config(text="Password must be more than 8 characters")
            new_password_entry.delete(0, tk.END)
            return
        if not re.search("[a-z]", password):
            password_result_label.config(text="Password must contain at least one lowercase letter")
            new_password_entry.delete(0, tk.END)
            return
        if not re.search("[A-Z]", password):
            password_result_label.config(text="Password must contain at least one uppercase letter")
            new_password_entry.delete(0, tk.END)
            return
        if not re.search("[0-9]", password):
            password_result_label.config(text="Password must contain at least one number")
            new_password_entry.delete(0, tk.END)
            return
        if not re.search("[_@!$?]", password):
            password_result_label.config(text="Password must contain at least one special character (_@!$?)")
            new_password_entry.delete(0, tk.END)
            return
        if re.search("\s", password):
            password_result_label.config(text="Password must not contain spaces")
            new_password_entry.delete(0, tk.END)
            return
        
        existing_user = cursor.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
        
        if existing_user:
            password_result_label.config(text="Username already exists. Please choose another.")
            new_password_entry.delete(0, tk.END)
            new_username_entry.delete(0, tk.END)
            connection.close()
            return

        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
            connection.commit()
            password_result_label.config(text="Password is valid and user saved!")
            new_password_entry.delete(0, tk.END)
            new_username_entry.delete(0, tk.END)
            #Waits 1 second then switches to  the Sign In tab
            password_result_label.after(1000, lambda: notebook.select(signin_frame))
        finally:
            connection.close()
    
class UserSignIn(UserInformation):
    def __init__(self, username, password):
        super().__init__(username, password)
    
    #Allowing the user to log in
    def SignIn(username, password):
        connection = sqlite3.connect('outerinator.db')
        cursor = connection.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user_verify = cursor.fetchone()
        
        #Boundary cases for logging in
        if username == "":
            SignIn_error_label.config(text="Please enter username")
        elif user_verify and user_verify[0] == password:
            SignIn_error_label.config(text="SignIn successful!")
            connection.close()
            #Waits 1 second then switches to the General page tab
            SignIn_error_label.after(1000, lambda: notebook.select(general_frame))
            return True
        elif user_verify:
            SignIn_error_label.config(text="Incorrect password.")
            connection.close()
            return False
        else:
            SignIn_error_label.config(text="Username not found.")
            connection.close()
            return False

#Coniguring rows and columns for the tabs
for n in range(4):
    signin_frame.grid_rowconfigure(n, weight=1)
    signup_frame.grid_rowconfigure(n, weight=1)
    
for n in range(1):
    signin_frame.grid_columnconfigure(n, weight=1)
    signup_frame.grid_columnconfigure(n, weight=1)
    
#Sign In tab
sign_username_label = tk.Label(signin_frame, text="Username:", font=("opensans_font", 14), fg="#001d75", bg="sky blue")
sign_username_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

username_entry = tk.Entry(signin_frame, font=("opensans_font", 14), fg="#001d75", bg="sky blue")
username_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

sign_password_label = tk.Label(signin_frame, text="Password:", font=("opensans_font", 14), fg="#001d75", bg="sky blue")
sign_password_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

password_entry = tk.Entry(signin_frame, show="*", font=("opensans_font", 14), fg="#001d75", bg="sky blue")
password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

go_to_signup = tk.Button(signin_frame, text="Go to Sign Up", font=("opensans_font", 14), fg="#001d75", bg="sky blue", command=lambda: notebook.select(signup_frame))
go_to_signup.grid(row=2, column=0, padx=10, pady=10)

SignIn_button = tk.Button(signin_frame, text="SignIn", font=("opensans_font", 14), fg="#001d75", bg="sky blue", command=lambda: UserSignIn.SignIn(username_entry.get(), password_entry.get()))
SignIn_button.grid(row=2, column=1, padx=10, pady=10)

SignIn_error_label = tk.Label(signin_frame, text="", font=("opensans_font", 12), fg="red")
SignIn_error_label.grid(row=3, columnspan=2, padx=10, pady=10)

#Sign up tab
sign_new_username_label = tk.Label(signup_frame, text="Enter a username:", font=("opensans_font", 14), fg="#001d75", bg="sky blue")
sign_new_username_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

new_username_entry = tk.Entry(signup_frame, font=("opensans_font", 14), fg="#001d75", bg="sky blue") 
new_username_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

sign_new_password_label = tk.Label(signup_frame, text="Enter a password\n(Must be more than 8 characters):", font=("opensans_font", 12), fg="#001d75", bg="sky blue")
sign_new_password_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

new_password_entry = tk.Entry(signup_frame, font=("opensans_font", 14), fg="#001d75", bg="sky blue")
new_password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

password_add_button = tk.Button(signup_frame, text="Add Password", command=lambda: PasswordValidator.is_valid(new_username_entry.get(), new_password_entry.get()), font=("opensans_font", 14), fg="#001d75", bg="sky blue")
password_add_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

password_result_label = tk.Label(signup_frame, text="", font=("opensans_font", 12), fg="green")
password_result_label.grid(row=2, column=1, padx=10, pady=10)

outerinator.mainloop()