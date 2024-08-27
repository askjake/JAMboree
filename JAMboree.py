from scp import SCPClient
import sys
import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime, timedelta, timezone
import subprocess
import glob
import ftplib
import threading
import shutil
import ipaddress
import paramiko
import sched
import time
from threading import Thread
import serial.tools.list_ports
import serial
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from commands import get_button_codes, get_sgs_codes
import re
from get_stb_list import *
import socket
from debug_gui import DebugGUI
from debug_gui import *
import logging 
import ast
from PIL import Image, ImageTk

# Set up logging
logging.basicConfig(filename='debugJam.log', level=logging.DEBUG)
logging.debug('JAMboree script started.')

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for the entire Flask app

# Append the directory containing sgs_lib to the system path
script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary
sys.path.append(script_dir)

config_file = 'base.txt'
credentials_file = 'credentials.json'
apps_list_file = 'apps_list.json'

class JAMboree_gui(tk.Tk):
    def __init__(self, *args, **kwargs):
        logging.debug('Initializing JAMboree GUI.')
        super().__init__(*args, **kwargs)
        
        self.ssh_client = None  
        computer_name = socket.gethostname()  # Get the computer's hostname
        logging.debug(f'Computer hostname: {computer_name}')
        
        self.title(f'{computer_name} - JAMboree')  # Set window title with computer name
        self.geometry('825x900')  # Adjust the size as needed        
        self.thin_geometry = '420x900'
        self.mid_geometry = '825x900'
        self.width = 1100
        self.height = 900
        self.full_geometry = f"{self.width}x{self.height}"
        self.proc = None 
        
        self.ssh_username_var = tk.StringVar()  # No default value
        self.ssh_password_var = tk.StringVar()  # No default value
        logging.debug('SSH variables initialized.')
        
        # Theme Colors
        self.bg_color = "#222222"  # Dark grey for background
        self.fg_color = "#ffffff"  # White for text
        self.btn_bg = "#555555"  # Lighter grey for buttons
        self.entry_bg = "#555555"  # Lighter grey for entries
        self.btn_fg = "#ffffff"  # White text for buttons
        logging.debug('Theme colors set.')
       
        # Load and resize the background image
        self.bg_image = Image.open("time-warp.jpg").resize((self.width, self.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)
        logging.debug('Background image loaded and resized.')

        # Create a canvas and set the background image
        self.canvas = tk.Canvas(self, width=self.width, height=self.height)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor='nw')
        logging.debug('Canvas created and background image set.')

        # Create a frame to hold the widgets
        self.frame = tk.Frame(self.canvas, bg='')  # Set background color to empty string
        self.frame.place(x=0, y=0, width=self.width, height=self.height)  # Adjust the placement as needed
        logging.debug('Main frame created and placed.')

        self.config_lock = threading.Lock()
        # Initialize storage lists
        self.entries = []
        self.comboboxes = []
        self.checkboxes = []
        self.checkbox_vars = []
        self.serial_connections = {}
        self.serial_connection = None
        self.config_file = 'base.txt'
        self.com_port = None  # This will store the current COM port
        self.linux_pc_var = tk.StringVar(value="10.79.97.129")  # Default to localhost
        self.linux_pc_history = []  # Store history for linux_pc_var        
        self.ssh_username_var = tk.StringVar(value="default_user")  # Default username
        self.ssh_password_var = tk.StringVar(value="default_password")  # Default password
        self.ssh_username_history = []
        self.config_data = {}
        self.button_press_times = {}  # Define before calling load_config
        self.output_text = tk.Text(self.frame, height=10, width=100, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.output_text.grid(row=18, column=0, columnspan=10, pady=5, padx=10, sticky='w')
        logging.debug('UI elements initialized.')

        self.unpair_sequence = ['Left', 'Down', 'Left', 'Right', 'Down', 'Right', 'Left', 'Left', 'Right', 'Right']  # was self.key_sequence
        self.debug_sequence = ['Left', 'Left', 'Right', 'Right', 'Up', 'Down', 'Up', 'Down']
        self.current_sequence = []
        self.unpair_btn = None  # This will hold the button widget once created
        self.load_credentials()  # Load credentials on startup
        
        logging.debug('Initial setup complete.')

        self.pin_entry = ttk.Entry(self.frame, style='TEntry', width=8)
        self.pin_entry.grid(row=19, column=1, columnspan=1, sticky='ew')
        
        self.sgs_pairing_instance = self.SGSPairing(self.output_text, self.pin_entry)

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        logging.debug('UI setup complete.')
        
         

        


    def __del__(self):
        logging.debug('Destroying JAMboree GUI instance.')
        self.close_all_serial_connections()
        if self.ssh_client:
            self.ssh_client.close()  # Ensure the SSH connection is closed when the instance is deleted
            logging.debug('SSH connection closed.')
        super().__del__()

    def setup_ui(self):
        logging.debug('Setting up UI components.')
        self.configure(bg=self.bg_color)  # Set the background color of the root window

        style = ttk.Style()
        style.theme_use('clam')  # This theme allows color customization
        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color, insertcolor=self.fg_color)  # Correct style for Entry
        style.configure("TButton", background=self.btn_bg, foreground=self.btn_fg, relief='flat')  # Button style
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)  # Label style
        style.configure("TCombobox", fieldbackground=self.entry_bg, background=self.btn_bg, foreground=self.fg_color)
        style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)])
        style.map('TCombobox', selectbackground=[('readonly', self.entry_bg)])
        style.map('TCombobox', selectforeground=[('readonly', self.fg_color)])
        style.configure("TCheckbutton", background=self.bg_color, foreground=self.fg_color, focuscolor=style.configure(".")["background"])
        style.map("TCheckbutton", background=[('active', self.bg_color), ('selected', self.bg_color)])
        logging.debug('UI styles configured.')

        self.credentials_frame = ttk.Frame(self)
        self.credentials_frame.pack(fill='both', expand=True)
        logging.debug('Credentials frame created and packed.')

        # Start Flask app in a separate thread
        self.flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False))
        self.flask_thread.start()
        logging.debug('Flask app started in a separate thread.')

        self.extra_column_visible = False  # Control visibility of the master column
        self.thin_mode_active = False  # Control visibility of the master column
        logging.debug('Initial UI state set.')

        # ttk.Label(self.frame, text='Select').grid(row=0, column=3)        
        ttk.Label(self.frame, text='STB Name', style='TLabel').grid(row=0, column=4, pady=(2,0), sticky='ew')
        ttk.Label(self.frame, text='STB RxID', style='TLabel').grid(row=0, column=5, pady=(2,0), sticky='ew')
        ttk.Label(self.frame, text='STB IP', style='TLabel').grid(row=0, column=6, pady=(2,0), sticky='ew')
        ttk.Label(self.frame, text='Joey''s Master', style='TLabel').grid(row=0, column=10)
        ttk.Label(self.frame, text='Linux IP', style='TLabel').grid(row=0, column=9)
        ttk.Label(self.frame, text='COM Port', style='TLabel').grid(row=0, column=8)

        # Check all checkbox
        self.all_var = tk.BooleanVar()
        self.check_all_btn = ttk.Checkbutton(self.frame, text="All", variable=self.all_var, command=self.check_all, style="TCheckbutton")
        self.check_all_btn.grid(row=0, column=3, sticky='ew')

        self.bind_all('<Key>', self.track_keys)

        # Protocol dropdown for all
        self.protocol_var = tk.StringVar()
        self.protocol_all_combo = ttk.Combobox(self.frame, values=['RF', 'SGS'], state='readonly', textvariable=self.protocol_var, width=8)
        self.protocol_all_combo.grid(row=0, column=7, sticky='w', padx=2, pady=(1,1))
        self.protocol_all_combo.set('RF / SGS')
        self.protocol_all_combo.bind('<<ComboboxSelected>>', self.set_all_protocols)
        
        self.stb_comboboxes = []  # List to keep all stb_name comboboxes   
        self.linux_pc_comboboxes = []  # List to keep all linux_pc comboboxes
        self.com_port_comboboxes = []  # List to keep all com_port comboboxes
        self.master_comboboxes = []
        
        for i in range(16):  # Assuming 16 rows
            master_combo = ttk.Combobox(self.frame, style='TCombobox', width=12)
            linux_pc_combo = ttk.Combobox(self.frame, style='TCombobox', width=12)
            com_port_combo = ttk.Combobox(self.frame, style='TCombobox', width=8)
            
            master_combo['values'] = self.find_hoppers()  # Method to retrieve list of Hoppers
            master_combo.bind("<<ComboboxSelected>>", lambda event, idx=i: self.update_master_stb(idx))
            
            master_combo.grid(row=i + 1, column=10, padx=3, pady=(1,1))
            linux_pc_combo.grid(row=i + 1, column=9, padx=3, pady=(1,1))
            com_port_combo.grid(row=i + 1, column=8, padx=3, pady=(1,1))

            #master_combo.grid_remove()  # Hide initially
            #linux_pc_combo.grid_remove()  # Hide initially
            #com_port_combo.grid_remove()  # Hide initially
            
            self.master_comboboxes.append(master_combo)
            self.linux_pc_comboboxes.append(linux_pc_combo)
            self.com_port_comboboxes.append(com_port_combo)
                
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.frame, text='#' + str(i+1), variable=var, style="TCheckbutton")
            chk.grid(row=i+1, sticky='ew', column=3, padx=2)
            self.checkbox_vars.append(var)
            self.checkboxes.append(chk)
            
            stb_combo = ttk.Combobox(self.frame, style='TCombobox', width=12)
            remote_index = str(i + 1)
            stb_combo.grid(row=i + 1, column=4)
            stb_combo.bind("<<ComboboxSelected>>", lambda event, idx=i: self.on_stb_select(idx))
            self.stb_comboboxes.append(stb_combo)

            for j in range(5, 7):  # Three entries: Name, RXID, IP 
                entry = ttk.Entry(self.frame, style='TEntry')
                entry.grid(row=i+1, column=j, padx=2)
                self.entries.append(entry)
                
            combo = ttk.Combobox(self.frame, values=['RF', 'SGS'], state='readonly', width=5)
            combo.grid(row=i+1, sticky='ew', column=7)
            self.comboboxes.append(combo)
            
        ttk.Label(self.frame, text='STB Name', style='TLabel').grid(row=17, column=4)
        ttk.Label(self.frame, text='STB RxID', style='TLabel').grid(row=17, column=5)
        ttk.Label(self.frame, text='STB IP', style='TLabel').grid(row=17, column=6)
        ttk.Label(self.frame, text='#', style='TLabel').grid(row=17, column=7)

        # ComboBoxes for STB Name, RxID, and IP
        self.stb_name_cb = ttk.Combobox(self.frame, style='TCombobox', width=15)
        self.stb_name_cb.grid(row=17, column=4, padx=2)
        self.stb_rxid_cb = ttk.Combobox(self.frame, style='TCombobox', width=15)
        self.stb_rxid_cb.grid(row=17, column=5, padx=2)
        self.stb_ip_cb = ttk.Combobox(self.frame, style='TCombobox', width=15)
        self.stb_ip_cb.grid(row=17, column=6, padx=2)

        # Entry for new remote number
        self.new_remote_entry = ttk.Entry(self.frame, foreground="grey" , width=5)
        self.new_remote_entry.insert(0, "#")
        self.new_remote_entry.grid(row=17, column=7)
        self.new_remote_entry.bind('<FocusIn>', self.entry_focus_in)
        self.new_remote_entry.bind('<FocusOut>', self.entry_focus_out)
        self.new_remote_entry.bind('<Return>', self.update_remote_value)

        # Bind comboboxes to a method that updates other fields
        self.stb_name_cb.bind("<<ComboboxSelected>>", self.update_related_fields)
        self.stb_rxid_cb.bind("<<ComboboxSelected>>", self.update_related_fields)
        self.stb_ip_cb.bind("<<ComboboxSelected>>", self.update_related_fields)
        
        #self.authorizations_btn = ttk.Button(self.frame, text="Get Auth's", command=self.authorizations, style='TButton')
        #self.authorizations_btn.grid(row=20, column=4, padx=2, pady=2)
        
        # Button to toggle Master Column visibility
        self.toggle_master_btn = ttk.Button(self.frame, text="Show Extras", command=self.toggle_master_column, style='TButton')
        self.toggle_master_btn.grid(row=19, column=4, padx=2)
        
        self.com_select = ttk.Combobox(self.frame, state="readonly")
        self.com_select.grid(row=1, columnspan=2, column=0, sticky='ew', padx=2)
        self.com_select.bind("<<ComboboxSelected>>", self.on_com_select)
        
        refresh_btn = ttk.Button(self.frame, text="Refresh", command=self.refresh, style='TButton')
        refresh_btn.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
        
        self.pin_submit_btn = ttk.Button(self.frame, text="PIN", command=self.sgs_pairing_instance.submit_pin)

        self.pin_submit_btn.grid(row=19, column=2, sticky='ew', padx=2)
        
        self.buttons = {
            'Power': ('1', 'p'),   
            'reset': ('reset', 'r'),     
            'dvr_guide': ('42', 'q'),
            'DVR': ('3', 'v'),    
            'Home': ('2', 'h'),   
            'Guide': ('4', 'g'),
            'Options': ('5', 'o'),  
            'Up': ('6', 'Up'),     
            'mic': ('7', 'm'),
            'Left': ('8', 'Left'),   
            'Enter': ('9', 'Enter'),  
            'Right': ('10', 'Right'),
            'Back': ('11', 'b'),  
            'Down': ('12', 'Down'),  
            'Info': ('13', 'i'),
            'RWD': ('14', 'r'),   
            'Play': ('15', 'p'),  
            'FWD': ('16', 'f'),
            '--- ': ('1', '2'),   
            'pair': ('pair', '2'),    
            ' ---': ('1', '2'),
            'vol+': ('17', 'V'),  
            'recall': ('18', 'R'),  
            'ch_up': ('19', 'C'),
            'vol-': ('20', 'v'),  
            'mute': ('21', 'm'),  
            'ch_down': ('22', 'c'),
            '- ': ('1', 'q'),     
            '-- ': ('1', 'q'),    
            ' --- ': ('1', 'q'),
            '1': ('23', '1'),     
            '2': ('24', '2'),     
            '3': ('25', '3'),
            '4': ('26', '4'),    
            '5': ('27', '5'),    
            '6': ('28', '6'),
            '7': ('29', '7'),      
            '8': ('30', '8'),      
            '9': ('31', '9'), 
            'd': ('32', 'd'),  
            '0': ('33', '0'),   
            'dd': ('34', 'D'), 
            'sat': ('35', 's'),    
            'tv': ('36', 't'),     
            'aux': ('37', 'a'), 
            'input': ('38', 'i'),   
            'upair1': ('39', 'p'),  
            'upair2': ('40', 'P'), 
        }
        
        # Create and place buttons in 3 columns
        row = 2
        col = 0
        for label, (button_id, key) in self.buttons.items():
            btn = ttk.Button(self.frame, text=label)
            btn.grid(row=row, column=col, sticky='ew', padx=2, pady=2)
            btn.bind("<ButtonPress>", lambda event, bid=button_id: self.start_timer(bid))
            btn.bind("<ButtonRelease>", lambda event, bid=button_id: self.process_button_press(event, bid))
            self.bind_all(f"<Control-{key}>", lambda event, bid=button_id: self.process_button_press(event, bid))  # This binds Ctrl + key

            col += 1
            if col > 2:
                col = 0
                row += 1

        # Bottom buttons
        self.thin_mode_active = False  # Track the visibility state of columns 4 and up
        self.toggle_thin_mode_btn = ttk.Button(self.frame, text="Skinny", command=self.toggle_thin_mode)
        self.toggle_thin_mode_btn.grid(row=20, column=4, padx=2)  
    
        save_btn = ttk.Button(self.frame, text="Save", command=self.save_config, style='TButton')
        save_btn.grid(row=20, column=1, sticky='ew', padx=2)
        
        open_DebugGUI_btn = ttk.Button(self.frame, text="Debug", command=self.open_DebugGUI, style='TButton')
        open_DebugGUI_btn.grid(row=1, column=2, sticky='ew', padx=2)
        
        pair_btn = ttk.Button(self.frame, text="pair", command=lambda: self.process_button_press(None, 'pair'), style='TButton')
        pair_btn.grid(row=19, column=0, sticky='ew', padx=2, pady=2)
        
        pair_btn = ttk.Button(self.frame, text="SGS Pair", command=lambda: self.SGSPairing.sgs_pair(), style='TButton')
        pair_btn.grid(row=20, column=0, sticky='ew', padx=2, pady=2)
        


        self.apply_dark_theme(self.frame)
        self.refresh()
        logging.debug('UI components setup complete.')

    def apply_dark_theme(self, parent):
        for widget in parent.winfo_children():
            widget_type = widget.winfo_class()
            if widget_type in ["TButton", "TLabel", "TEntry", "TCombobox"]:
                widget.configure(style=widget_type)  # Apply the respective style
            elif isinstance(widget, tk.Text):
                widget.configure(bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
            if widget.winfo_children():
                self.apply_dark_theme(widget)

    def load_credentials(self):
        os.chdir(script_dir)
        try:
            with open(credentials_file, 'r') as file:
                credentials = json.load(file)
                self.ssh_username_var.set(credentials.get('username', ''))
                self.ssh_password_var.set(credentials.get('password', ''))
                print(f"Credentials loaded. {self.ssh_username_var}")
        except FileNotFoundError:
            print("Credentials file not found.")
        except json.JSONDecodeError:
            print("Error decoding credentials file.")

    def toggle_master_column(self):
        # Toggle the visibility of the master columns (8, 9, and 10)
        columns_to_toggle = [8, 9, 10]
        if self.extra_column_visible:
            for widget in self.grid_slaves():
                widget_col = int(widget.grid_info().get("column", 0))
                if widget_col in columns_to_toggle:
                    widget.grid_remove()
            self.extra_column_visible = False
        else:
            for widget in self.grid_slaves():
                widget_col = int(widget.grid_info().get("column", 0))
                if widget_col in columns_to_toggle:
                    widget.grid()
            self.extra_column_visible = True

        # Update layout and resize window after toggling widget states
        self.update_idletasks()
        if self.extra_column_visible:
            self.geometry(self.full_geometry)
        else:
            self.geometry(self.mid_geometry)
            
    def toggle_thin_mode(self):
        # Determine which columns to hide or show based on the current state
        start_column = 4  # Start toggling from column 4
        columns_to_toggle = [4, 5, 6, 7, 9, 10]  # Include columns you want to toggle

        if self.thin_mode_active:
            # Currently in thin mode, need to show all widgets from start_column onwards
            for widget in self.grid_slaves():
                widget_col = int(widget.grid_info().get("column", 0))
                if widget_col >= start_column or widget_col in columns_to_toggle:
                    print(f"Showing widget at column {widget_col}")
                    widget.grid()  # Reinstate the grid placement for the widget
            self.thin_mode_active = False  # Toggle the state
            print("Switched to full mode")
            #self.close_and_reopen()
        else:
            # Not in thin mode, need to hide widgets from start_column onwards
            for widget in self.grid_slaves():
                widget_col = int(widget.grid_info().get("column", 0))
                if widget_col >= start_column or widget_col in columns_to_toggle:
                    #print(f"Hiding widget at column {widget_col}")
                    widget.grid_remove()  # Remove the widget from the grid
            self.thin_mode_active = True  # Toggle the state
            print("Switched to thin mode")

        # Update layout and resize window after toggling widget states
        self.update_idletasks()
        if self.thin_mode_active:
            self.geometry(self.thin_geometry)  # Smaller, predefined size for thin mode
        else:
            self.geometry(self.full_geometry)  # Reset to full geometry

    def send_reset_and_sat(self):
        self.rf_remote(com_port, '1', 'reset', 80)
        for remote in range(1, 16):
            self.rf_remote(str(remote), 'sat', 80)
        print("Sent reset and SAT to all remotes")
    
    def schedule_reset_and_sat(self):
        self.send_reset_and_sat()
        self.scheduler.enter(600, 1, self.schedule_reset_and_sat)
        
    def ensure_ssh_connection(self, linux_pc):
        logging.debug(f"Ensuring SSH connection to {linux_pc}.")
        try:
            if self.ssh_client is None:
                logging.debug("Creating new SSH client instance.")
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                logging.debug("Establishing SSH connection.")
                self.ssh_client.connect(linux_pc, username=self.ssh_username_var.get(), password=self.ssh_password_var.get())
                self.output_text.insert(tk.END, "Connected to proxy. \n")
                logging.info(f"Successfully connected to {linux_pc} via SSH.")
        except paramiko.AuthenticationException:
            logging.error("SSH Authentication failed.")
            self.output_text.insert(tk.END, "Authentication failed, please check your username or password.\n")
        except paramiko.SSHException as e:
            logging.error(f"SSH error: {str(e)}")
            self.output_text.insert(tk.END, f"SSH error: {str(e)}\n")
        except Exception as e:
            logging.error(f"Connection error: {str(e)}")
            self.output_text.insert(tk.END, f"Connection error: {str(e)}\n")
            self.ssh_client = None  # Reset ssh_client if connection fails
        
    def call_get_dev_logs(self):
        os.chdir(script_dir)
        linux_pc = self.linux_pc_var.get()
        ssh_username = self.ssh_username_var.get()
        any_selected = False
        
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():
                any_selected = True
                stb_ip = self.entries[idx * 2 + 1].get()
                hopper_rid = self.entries[idx * 2].get()
                Thread(target=self.get_dev_logs, args=(linux_pc, stb_ip, hopper_rid, ssh_username)).start()
                #Thread(target=self.old_get_dev_logs, args=(linux_pc, stb_ip, hopper_rid, ssh_username)).start()
        
        if not any_selected:
            self.output_text.insert(tk.END, "No STB selected!\n")
            self.output_text.see(tk.END)

    def get_dev_logs(self, linux_pc, stb_ip, hopper_rid, ssh_username, retry=False):
        date  = datetime.now().strftime('%Y-%m-%d')
        log_folder = f'{hopper_rid}/{date}'
        password = self.ssh_password_var.get()
        retries = 3  # Number of retries for authentication
        ftp_server = "10.74.139.250"
        studio = "10.74.139.250"
        studio_username = "dishiptest"
        studio_password = "Dish1234"
        studio_directory = f"/dishiptest/smplogs/{log_folder}"
        linux_pc_dir = f"/home/diship/stbmnt/smplogs/{log_folder}"
        ftp_username = "dishiptest"
        ftp_password = "Dish1234"
        ftp_directory =  f'smplogs/{log_folder}'
        studio_dir =     f'/smplogs/{log_folder}'

        for attempt in range(retries):
            try:
                # Establish SSH connection
                print("Connecting to Linux PC...")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(linux_pc, username=ssh_username, password=password)
                print("Connected to Linux PC.")
                shell = ssh.invoke_shell()

                # Get the current date
                date = datetime.now().strftime('%Y-%m-%d')

                # Ensure the local directory exists
                if not os.path.exists(linux_pc_dir):
                    os.makedirs(linux_pc_dir)

                # Create the necessary directory if it doesn't exist
                commands = [
                    f'mkdir -p {linux_pc_dir}',
                    f'./stbmnt/tnet {stb_ip}  {ftp_directory}',
                    f'cp /var/mnt/MISC_HD/nal_0.cur nal_0.cur'
                ]  

                # Execute commands to create directory and run the initial command
                for command in commands:
                    shell.send(f"{command}\n")
                    print(f"Executing command: {command.strip()}")
                    time.sleep(5)  # Give some time for the command to execute

                # Function to capture the output of a command
                def run_command(command):
                    shell.send(f"{command}\n")
                    print(f"Running command: {command}")
                    time.sleep(0.25)  # Increase sleep time for command execution
                    output = ""
                    while True:
                        if shell.recv_ready():
                            output += shell.recv(1024).decode('utf-8')
                        else:
                            break
                    print(f"Command output: {output}")
                    self.output_text.insert(tk.END, output)
                    self.output_text.see(tk.END)
                    return output

                # Wait for the specific prompt or error before proceeding
                device_busy = False
                device_reboot = False
                while True:
                    output = shell.recv(1024).decode('utf-8')
                    self.output_text.insert(tk.END, output)
                    self.output_text.see(tk.END)
                    if '/home #' in output:
                        break
                    if "busy" in output:
                        device_busy = True
                        break
                    if "fail" in output:
                        device_reboot = True
                        break

                if device_busy:
                    self.output_text.insert(tk.END, "Device or resource busy detected. unmounting...\n")
                    self.output_text.see(tk.END)
                    run_command('umount -l /home')
                    time.sleep(1)
                    self.get_dev_logs(linux_pc, stb_ip, hopper_rid, ssh_username, retry=True)
                    return

                if device_reboot:
                    self.output_text.insert(tk.END, "Device rebooting...\n")
                    self.output_text.see(tk.END)
                    run_command('reboot')
                    time.sleep(300)
                    self.get_dev_logs(linux_pc, stb_ip, hopper_rid, ssh_username, retry=True)
                    return

                # Get the list of folders in '/var/mnt/MISC_HD/esosal_log/'
                esosal_output = run_command('ls -1 /var/mnt/MISC_HD/esosal_log/')
                esosal_folders = [folder.strip() for folder in esosal_output.split('\n') if folder.strip() and not folder.startswith('total')]

                # Log the esosal folders for debugging
                self.output_text.insert(tk.END, f"Esosal folders: {esosal_output}\n")
                self.output_text.see(tk.END)

                # Copy files from esosal_log
                for folder in esosal_folders:
                    command = f'cp /var/mnt/MISC_HD/esosal_log/{folder}/{folder}.0 {folder}.0'
                    run_command(command)

                # Get the list of folders in '/var/mnt/MISC_HD/joey_logs/'
                joey_output = run_command('ls -1 /var/mnt/MISC_HD/joey_logs/')
                joey_folders = [folder.strip() for folder in joey_output.split('\n') if folder.strip() and not folder.startswith('total')]

                # Log the joey folders for debugging
                self.output_text.insert(tk.END, f"Joey folders: {joey_folders}\n")
                self.output_text.see(tk.END)

                # Copy files from joey_logs
                for joeyRID in joey_folders:
                    command = f'cp /var/mnt/MISC_HD/joey_logs/{joeyRID}/nal_0.cur {joeyRID}_nal_0.cur'
                    run_command(command)
                    command = f'cp /var/mnt/MISC_HD/joey_logs/{joeyRID}/nal/nal {joeyRID}_nal.txt'
                    run_command(command)

                run_command('exit')

                # Re-establish SSH connection to Studio
                studio = "10.74.139.250"
                studio_username = "dishiptest"
                studio_password = "Dish1234"
                
                #run_command(f'scp /home/diship/stbmnt/smplogs/* {studio_username}@{studio}/smplogs/ ')

                print("Connecting to Studio for SCP...")
                ssh_studio = paramiko.SSHClient()
                ssh_studio.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_studio.connect(studio, username=studio_username, password=studio_password)
                print("Connected to Studio.")

                # Ensure the directory exists on the Studio machine
                print(f"Creating directory on Studio: {studio_directory}")
                stdin, stdout, stderr = ssh_studio.exec_command(f'mkdir -p {studio_directory}')
                stdout.channel.recv_exit_status()  # Wait for the command to finish
                print("Directory created on Studio.")

                # List files in linux_pc_dir before SCP
                stdin, stdout, stderr = ssh.exec_command(f'ls -1 {linux_pc_dir}')
                file_list = stdout.read().decode('utf-8').strip().split('\n')
                print(f"Files in {linux_pc_dir}:\n{file_list}")
                self.output_text.insert(tk.END, f"Files in {linux_pc_dir}:\n{file_list}\n")
                self.output_text.see(tk.END)

                # SCP files from Linux PC to Studio
                print(f"SCP files from Linux PC to Studio: {linux_pc_dir} -> {studio_directory}")
                scp = SCPClient(ssh_studio.get_transport())

                for file_name in file_list:
                    file_name = file_name.strip()  # Remove any extraneous whitespace
                    print(f"File: {file_name}\n")
                    print(f'{linux_pc_dir}/{file_name}', f'{ftp_directory}/{file_name}')
                    self.output_text.insert(tk.END, f"File: {file_name}\n")
                    self.output_text.see(tk.END)
                    scp.put(f'{linux_pc_dir}/{file_name}', f'{ftp_directory}/{file_name}')
                    #scp.send(f'{ftp_directory}/{file_name}',  preserve_times=True, progress=progress)
                    
                    '''
                    if file_name:  # Ensure it's not an empty line
                        linux_path = f'stbmnt/{ftp_directory}/{file_name}'
                        studio_path = f'{studio_directory}/{file_name}'
                        print(f"Copying {linux_path} to {studio_path}")
                        self.output_text.insert(tk.END, f"Copying {linux_path} to {studio_path}\n")
                        self.output_text.see(tk.END)
                        scp.put(f'{linux_pc_dir}/{file_name}', studio_path)
                        #scp.put(linux_path, studio_path)
                        
                        #run_command(f'scp {studio_username}@{studio}/{remote_path} {local_path} ')
                        '''

                scp.close()
                print("SCP transfer completed.")

                # Close the SSH connection to Studio
                ssh_studio.close()
                print("Closed SSH connection to Studio.")

                # Close the SSH connection to Linux PC
                ssh.close()
                print("Closed SSH connection to Linux PC.")

                break

            except paramiko.AuthenticationException:
                self.output_text.insert(tk.END, "Authentication failed. Please re-enter your password.\n")
                self.output_text.see(tk.END)
                password = self.get_password(linux_pc, ssh_username)

            except Exception as e:
                self.output_text.insert(tk.END, f"Error: {str(e)}\n")
                self.output_text.see(tk.END)
                break

    def get_password(self, linux_pc, ssh_username):
        # Create a temporary window to get the new password
        password_window = tk.Toplevel(self)
        password_window.title("Re-enter Password")

        tk.Label(password_window, text=f"Linux PC: {linux_pc}\nUsername: {ssh_username}").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        tk.Label(password_window, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        password_var = tk.StringVar()
        password_entry = tk.Entry(password_window, textvariable=password_var, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=5)

        def on_submit():
            self.ssh_password_var.set(password_var.get())
            password_window.destroy()

        submit_btn = tk.Button(password_window, text="Submit", command=on_submit)
        submit_btn.grid(row=2, columnspan=2, pady=5)

        password_window.grab_set()  # Make the new window modal
        self.wait_window(password_window)
        return self.ssh_password_var.get()

    def close_and_reopen(self):
        # Close the current application
        self.save_config()
        self.close_all_serial_connections()
        self.destroy()

        # Reopen the application
        threading.Thread(target=self.reopen_application).start()

    def reopen_application(self):
        # Create a new instance of the application
        new_app = JAMboree_gui()
        new_app.mainloop()

    def entry_focus_in(self, event):
        if self.new_remote_entry.get() == 'enter new #':
            self.new_remote_entry.delete(0, tk.END)
            self.new_remote_entry.config(foreground='black')

    def entry_focus_out(self, event):
        if not self.new_remote_entry.get():
            self.new_remote_entry.insert(0, 'enter new #')
            self.new_remote_entry.config(foreground='grey') 
 
    def track_keys(self, event):
        key_name = event.keysym  # This gets the name of the key pressed
        logging.debug(f"Key pressed: {key_name}")
        if key_name in ['Left', 'Right', 'Up', 'Down']:  # Only track arrow keys
            self.current_sequence.append(key_name)
            logging.debug(f"Current sequence: {self.current_sequence}")

            # Check if the current sequence matches the prefix of the target sequence
            if (self.current_sequence != self.debug_sequence[:len(self.current_sequence)] and
                self.current_sequence != self.unpair_sequence[:len(self.current_sequence)]):
                logging.debug("Sequence mismatch, resetting sequence.")
                self.current_sequence = []  # Reset if any mismatch

            if self.current_sequence == self.unpair_sequence:
                logging.info("Unpair sequence detected.")
                self.show_unpair_button()
                self.current_sequence = []  # Reset sequence

            if self.current_sequence == self.debug_sequence:
                logging.info("Debug sequence detected.")
                self.open_DebugGUI()
                self.current_sequence = []  # Reset sequence
            
    def open_video_ui(self):
        if not hasattr(self, 'video_ui') or not self.video_ui.winfo_exists():
            self.video_ui = VideoUI(self)
        self.video_ui.lift()  # Bring the debug menu to the front       

    def open_DebugGUI(self):
        if not hasattr(self, 'DebugGUI') or not self.DebugGUI.winfo_exists():
            self.DebugGUI = DebugGUI(self)
        self.DebugGUI.lift()  # Bring the debug menu to the front                
        print("Sequence matched - Opening menu")  # Debugging output

    def show_video_button(self):
        if not self.show_video_btn:  # Create the button if it doesn't exist
            self.show_video = ttk.Button(self, text='Show Me', command=self.open_video_ui)
        self.show_video.grid(row=0, column=2, sticky='ew', padx=1, pady=1)
        self.show_video.lift()  # This makes the button visible
        print("Video Button shown")  # Debugging output
       
    def hide_video_button(self):
        if self.show_video:
            self.show_video.grid_remove()  # This hides the button but does not destroy it
        print("Button hidden")  # Debugging output
        
    def show_unpair_button(self):
        if not self.unpair_btn:  # Create the button if it doesn't exist
            self.unpair_btn = ttk.Button(self, text='Unpair', command=self.unpair_function)
        self.unpair_btn.grid(row=0, column=1)
        self.unpair_btn.lift()  # This makes the button visible
        print("Button shown")  # Debugging output
        
    def hide_unpair_button(self):
        if self.unpair_btn:
            self.unpair_btn.grid_remove()  # This hides the button but does not destroy it
        print("Button hidden")  # Debugging output

    def unpair_function(self):        
        os.chdir(script_dir)
        pygame.mixer.music.load('undo.mp3')        
        pygame.mixer.music.play(-1)
        print("Unpairing...")
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():  # Check if the checkbox for the STB is selected
                remote = str(idx + 1)
                self.rf_remote(self.com_port, remote, 'sat', 3100)  # Press and hold 'sat' button
                self.after(3100, lambda: self.rf_remote(self.com_port, remote, 'pair_down', 80))  # Press 'pair_down'
                self.after(6200, lambda: self.rf_remote(self.com_port, remote, 'pair_up', 80))  # Press 'pair_up' after previous delay
        self.after(6200, self.hide_unpair_button)
        pygame.mixer.music.stop()
        
    def mark_logs(self):
        logging.info("Marking logs.")
        self.process_button_press(None, '13')
        self.after(3000, lambda: self.process_button_press(None, '38'))
        self.after(5000, lambda: self.process_button_press(1000, '11'))
        logging.debug("Log marking sequence executed.")

    def update_related_fields(self, event):
        selected_index = event.widget.current()
        #logging.debug(f"Updating related fields based on selected index: {selected_index}")
        # Assuming that all comboboxes have the same index for related items
        self.stb_name_cb.current(selected_index)
        self.stb_rxid_cb.current(selected_index)
        self.stb_ip_cb.current(selected_index)
        #logging.info(f"Related fields updated for index: {selected_index}")
        self.save_config()

    def update_remote_value(self, event):
        new_remote = self.new_remote_entry.get().strip()
        logging.debug(f"Updating remote value to: {new_remote}")
        if new_remote and new_remote != 'enter new #':
            selected_stb_name = self.stb_name_cb.get()
            if selected_stb_name:
                logging.info(f"Updating remote for STB: {selected_stb_name} to {new_remote}")
                self.update_remote_in_config(selected_stb_name, new_remote)
                self.refresh()  # Refresh the GUI
            self.new_remote_entry.delete(0, tk.END)
            self.entry_focus_out(None)  # Reset the placeholder text

    def update_remote_in_config(self, stb_name, new_remote):
        logging.debug(f"Updating remote in config for {stb_name} to {new_remote}")
        os.chdir(script_dir)
        try:
            with open(self.config_file, 'r') as file:
                config_data = json.load(file)
            if stb_name in config_data['stbs']:
                config_data['stbs'][stb_name]['remote'] = new_remote  # Update the remote value
                with open(config_file, 'w') as file:
                    json.dump(config_data, file, indent=4)
                logging.info(f"Remote updated for {stb_name} to {new_remote}")
        except Exception as e:
            logging.error(f"Failed to update remote in config for {stb_name}: {str(e)}")        
        
    def find_hoppers(self):
        try:
            os.chdir(script_dir)
            with open(self.config_file, 'r') as file:
                config_data = json.load(file)
    
            # Check if 'stbs' key is in the dictionary to avoid KeyError
            if 'stbs' in config_data:
                # Filter and return STBs that are not Joey models
                return[stb_name for stb_name, stb_details in config_data['stbs'].items() if stb_details.get('model') != 'Joey']
            return []  # Return an empty list if 'stbs' is not available or no non-Joey models are found
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return []  # Return an empty list in case of an error

    def update_master_stb(self, idx):
        try:
            # Load the current configuration data
            os.chdir(script_dir)
            with open(self.config_file, 'r') as file:
                config_data = json.load(file)

            # Get selected master STB details
            selected_master = self.master_comboboxes[idx].get()
            master_data = config_data['stbs'].get(selected_master)
        
        
            # Get the currently selected Joey
            selected_joey = self.stb_comboboxes[idx].get()

            if master_data and selected_joey in config_data['stbs']:
                # Copy master's IP and RID to the Joey's config
                joey_data = config_data['stbs'][selected_joey]
                joey_data['master_stb'] = selected_master
                joey_data['rid'] = master_data['stb']  # Assuming 'stb' is the key for RID in master data
                joey_data['ip'] = master_data['ip']

                # Save updated configuration back to the file
                with open(self.config_file, 'w') as file:
                    json.dump(config_data, file, indent=4)

                print(f"Updated master for {selected_joey} to {selected_master}, IP: {master_data['ip']}, RID: {master_data['stb']}")
            self.refresh()

        except FileNotFoundError:
            print("Configuration file not found.")
        except json.JSONDecodeError:
            print("Error decoding JSON from the configuration file.")
        except KeyError as e:
            print(f"Key error: {e} - Check your configuration data integrity.")
         
    def on_stb_select(self, idx):
        """Update the entry fields based on selected stb_name."""
        stb_name = self.stb_comboboxes[idx].get()
        data = self.config_data["stbs"].get(stb_name, {})
        base_index = idx * 2
        self.entries[base_index].delete(0, tk.END)
        self.entries[base_index].insert(0, data.get('stb', ''))
        self.entries[base_index + 1].delete(0, tk.END)
        self.entries[base_index + 1].insert(0, data.get('ip', ''))
        self.comboboxes[idx].set(data.get('protocol', ''))
        
        self.linux_pc_comboboxes[idx].set(data.get('linux_pc', ''))
        self.master_comboboxes[idx].set(data.get('master_stb', ''))
        self.com_port_comboboxes[idx].set(data.get('com_port', ''))

        # Update selection state
        for key, value in self.config_data["stbs"].items():
            value["selected"] = (key == stb_name)
        self.save_config()

        # Save updated configuration back to the file
        with open(self.config_file, 'w') as file:
            json.dump(self.config_data, file, indent=4)

    def check_all(self):
        """Toggle all checkboxes based on the state of the 'Check All' checkbox."""
        is_checked = self.all_var.get()
        for var in self.checkbox_vars:
            var.set(is_checked)
        self.save_config()

    def set_all_protocols(self, event):
        protocol = self.protocol_var.get()
        logging.debug(f"Setting all protocols to: {protocol}")
        for combo in self.comboboxes:
            combo.set(protocol)
        self.save_config()
        logging.info(f"All protocols set to {protocol} and configuration saved.")

    def start_timer(self, button_id):
        self.button_press_times[button_id] = int(time.time() * 1000)
        logging.debug(f"Timer started for button ID: {button_id}.")

    def on_com_select(self, event=None):
        selected_com_port = self.com_select.get().split(' ')[-1].strip('()')
        logging.debug(f"COM port selected: {selected_com_port}")
        if selected_com_port and (selected_com_port != self.com_port):
            self.com_port = selected_com_port  # Update the current COM port
            self.open_serial_connection(self.com_port)
            logging.info(f"Serial connection opened on COM port: {self.com_port}")

    def open_serial_connection(self, com_port):
        logging.debug(f"Attempting to open serial connection on COM port: {com_port}")
        if com_port not in self.serial_connections or not self.serial_connections[com_port].is_open:
            if com_port in self.serial_connections:
                self.serial_connections[com_port].close()  # Close existing connection if open
            try:
                self.serial_connection = serial.Serial(
                    port=com_port,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS, 
                    parity=serial.PARITY_NONE, 
                    stopbits=serial.STOPBITS_ONE, 
                    timeout=1
                )
                self.output_text.insert(tk.END, f"Opened: {com_port}\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
                logging.info(f"Serial connection opened on {com_port}.")
            except serial.SerialException as e:
                logging.error(f"Failed to open serial port {com_port}: {str(e)}")
                self.output_text.insert(tk.END, f"Failed to open serial port: {str(e)}\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
                self.serial_connection = None

    def close_serial_connection(self, com_port):
        logging.debug(f"Closing serial connection on COM port: {com_port}")
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.close_all_serial_connections()
            logging.info(f"Serial connection closed on {com_port}.")

    def close_all_serial_connections(self):
        logging.debug("Closing all serial connections.")
        for com_port, connection in self.serial_connections.items():
            if connection and connection.is_open:
                connection.close()
                self.output_text.insert(tk.END, f"Closed serial port: {com_port}\n")
                self.output_text.see(tk.END)
                logging.info(f"Serial port {com_port} closed.")

    def save_config(self):
        os.chdir(script_dir)
        logging.debug("Saving configuration.")
        try:
            with open(self.config_file, 'r') as file:
                config_data = json.load(file)

            # Reset all entries to "is_recent": "false"
            for stb in config_data["stbs"].values():
                stb["is_recent"] = "false"
                #logging.debug(f"Set is_recent to false for STB.")

            entries_per_row = 2
            num_rows = len(self.entries) // entries_per_row

            for idx in range(num_rows):
                base_index = idx * entries_per_row
                stb_name = self.stb_comboboxes[idx].get() if idx < len(self.stb_comboboxes) else ""
                rxid = self.entries[base_index].get()
                stb_ip = self.entries[base_index + 1].get()
                protocol = self.comboboxes[idx].get()
                selected = self.checkbox_vars[idx].get()
                is_recent = "true" if stb_name else "false"
                linux_pc = self.linux_pc_comboboxes[idx].get() if idx < len(self.linux_pc_comboboxes) else ""
                com_port = self.com_port_comboboxes[idx].get() if idx < len(self.com_port_comboboxes) else ""

                if stb_name:
                    # Update or create new STB entry preserving existing data
                    stb_data = config_data["stbs"].get(stb_name, {})
                    stb_data.update({
                        "stb": rxid,
                        "protocol": protocol,
                        "selected": selected,
                        "ip": stb_ip,
                        "com_port": com_port,
                        "linux_pc": linux_pc,
                        "remote": str(idx + 1),
                        "is_recent": is_recent
                    })
                    config_data["stbs"][stb_name] = stb_data
                    #logging.debug(f"Updated STB {stb_name} in config.")
    
                elif stb_name:
                    # Create a new entry if it does not exist
                    config_data["stbs"][stb_name] = {
                        "stb": rxid,
                        "protocol": protocol,
                        "selected": selected,
                        "ip": stb_ip,
                        "prod": 'true',
                        "com_port": com_port,
                        "linux_pc": linux_pc,
                        "remote": str(idx + 1),
                        "is_recent": is_recent
                    }
                    logging.debug(f"Created new STB entry for {stb_name}.")
    
            if self.com_port:
                config_data["com_port"] = self.com_port
                logging.debug(f"Updated COM port in config: {self.com_port}")

            with open(self.config_file, 'w') as file:
                json.dump(config_data, file, indent=4)
                logging.info("Configuration saved.")

            self.config_data = config_data
        except Exception as e:
            logging.error(f"Failed to save configuration: {str(e)}")

    def load_config(self):
        self.stb_by_remote = {}
        os.chdir(script_dir)
        #logging.debug("Loading configuration.")
        try:
            with open(self.config_file, 'r') as file:
                self.config_data = json.load(file)
                #logging.debug("Configuration file loaded.")

            com_port = self.config_data.get("com_port", None)  # Load the COM port safely

            # Check and refresh available COM ports
            available_ports = self.find_serial_ports()
            logging.debug(f"Available COM ports: {available_ports}")
            self.com_select['values'] = [f"{name}" for name in available_ports]

            # Attempt to open the serial connection
            if com_port:
                self.com_port = com_port
                self.open_serial_connection(com_port)  # Safely open the connection with error handling
                logging.info(f"Opened serial connection on COM port: {com_port}")

            stbs_discovered = [stb for stb in self.config_data.get("stbs", {}).values() if str(stb.get('remote')) == "0"]
            self.stb_name_cb['values'] = [name for name, stb in self.config_data["stbs"].items() if str(stb.get('remote')) == "0"]
            self.stb_rxid_cb['values'] = [stb['stb'] for stb in stbs_discovered]  # Correct key for RxID
            self.stb_ip_cb['values'] = [stb['ip'] for stb in stbs_discovered]
            #logging.debug(f"STBs discovered: {stbs_discovered}")

            if stbs_discovered:
                # Automatically select the first entry by default (if it exists)
                self.stb_name_cb.current(0)
                self.stb_rxid_cb.current(0)
                self.stb_ip_cb.current(0)
                logging.info("Automatically selected first STB entry.")

            for idx in range(len(self.checkbox_vars)):
                remote_index = str(idx + 1)
                relevant_stbs = [name for name, data in self.config_data["stbs"].items() if data.get("remote") == remote_index]
                sorted_stbs = sorted(relevant_stbs, key=lambda x: self.config_data["stbs"][x].get("is_recent", "false"), reverse=True)
                self.stb_comboboxes[idx]['values'] = relevant_stbs  # Populate the combobox with all relevant STBs

                if sorted_stbs:
                    stb_name = sorted_stbs[0]  # Assume the first STB is the one to load
                    data = self.config_data["stbs"].get(stb_name, {})
                    base_index = idx * 2
                    self.stb_comboboxes[idx].set(stb_name)
                    self.entries[base_index].delete(0, tk.END)
                    self.entries[base_index].insert(0, data.get("stb", ''))
                    self.entries[base_index + 1].delete(0, tk.END)
                    self.entries[base_index + 1].insert(0, data.get("ip", ''))
                    self.comboboxes[idx].set(data.get("protocol", ''))
                    self.checkbox_vars[idx].set(data.get("selected", False))
                    self.linux_pc_comboboxes[idx]['values'] = self.get_combobox_values(data.get("linux_pc", ''), self.config_data["stbs"], "linux_pc")
                    self.linux_pc_comboboxes[idx].set(data.get("linux_pc", ''))
                    self.master_comboboxes[idx]['values'] = self.get_combobox_values(data.get("master_stb", ''), self.config_data["stbs"], "master_stb")
                    self.master_comboboxes[idx].set(data.get("master_stb", ''))
                    self.com_port_comboboxes[idx]['values'] = self.get_combobox_values_with_available_ports(data.get("com_port", ''), available_ports)
                    self.com_port_comboboxes[idx].set(data.get("com_port", ''))
                    #logging.info(f"Loaded configuration for STB: {stb_name}.")
        except Exception as e:
            logging.error(f"Failed to load configuration: {str(e)}")

    def get_combobox_values(self, saved_value, stbs, key):
        values = list({data[key] for data in stbs.values() if key in data})  # Use a set to remove duplicates
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        #logging.debug(f"Combobox values for {key} generated: {values}")
        return values

    def get_combobox_values_with_available_ports(self, saved_value, available_ports):
        values = available_ports[:]
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        #logging.debug(f"Combobox values with available ports generated: {values}")
        return values

    def find_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        friendly_ports = [port.description.split(' ')[-1].strip('()') for port in ports]
        logging.debug(f"Found serial ports: {friendly_ports}")
        return friendly_ports

    def refresh(self):
        self.load_config()

    def find_sgs(self):
        
        os.chdir(script_dir)
        pygame.mixer.music.load('loading.mp3')
        pygame.mixer.music.play(-1)
        
        subnets = get_subnets_from_arp()
        if not subnets:
            print("No subnets found.")
            return

        ip_list = discover_ips(subnets)
        
        for ip in ip_list:
            Thread(target=do_ips, args=(ip,)).start()
        
        '''
        from concurrent.futures import ThreadPoolExecutor
        # Run get_stb_info concurrently for the list of IPs
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(do_ips, ip) for ip in ip_list]
            results = []
            for future in futures:
                result = future.result()  # Getting the result to handle exceptions if any
                if result:
                    results.append(result)
                    self.output_text.insert(tk.END, f"{result}")
                    self.output_text.see(tk.END)
            #print("Processed results")
           '''
        self.refresh()
        pygame.mixer.music.stop()
    
    def process_button_press(self, event, button_id, stb_name=None):
        logging.debug(f"Processing button press for button ID: {button_id}, STB Name: {stb_name}")
        start_time = self.button_press_times.get(button_id, int(time.time() * 1000))
        end_time = int(time.time() * 1000)
        delay = end_time - start_time
        button_name = next((name for name, ids in self.buttons.items() if ids[0] == button_id), "Unknown")
        logging.debug(f"Button pressed: {button_name} with delay: {delay}ms")

        self.save_config()

        if button_id == 'reset':
            logging.info("Processing reset command for all COM ports.")
            all_com_ports = self.find_serial_ports()
            for com_port in all_com_ports:
                self.rf_remote(com_port, '1', button_id, delay)  # Assumes '1' is a valid remote ID for all cases

        elif button_id == 'pair':
            logging.info("Processing pairing sequence.")
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if details.get('selected')}
                updated = False
                for stb_name, stb_details in selected_stbs.items():
                    rxid = stb_details.get('stb', '')[:11]
                    stb_ip = stb_details.get('ip', '')
                    logging.debug(f"Pairing STB: {stb_name} with RxID: {rxid} and IP: {stb_ip}")
                    self.sgs_pairing_instance.sgs_pair(stb_name, stb_ip, rxid)
                    updated = True
                if updated:
                    logging.info("Pairing configurations updated successfully.")
                else:
                    logging.warning("No STBs were selected for pairing.")

            except Exception as e:
                logging.error(f"Failed to process SGS Pair: {str(e)}")
                self.output_text.insert(tk.END, f"Failed to process SGS Pair: {e}\n")
                self.output_text.see(tk.END)
        else:
            logging.info(f"Processing command for button ID: {button_id}")
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if details.get('selected')}
                for stb_name, stb_details in selected_stbs.items():
                    rxid = stb_details.get('stb', '')[:11]
                    stb_ip = stb_details.get('ip', '')
                    protocol = stb_details.get('protocol', '').lower()
                    com_port = stb_details.get('com_port', '')
                    remote = stb_details.get('remote', '')
                    command = button_name
                    logging.debug(f"Processing command for STB: {stb_name}, Protocol: {protocol}")

                    if protocol == 'sgs':
                        thread = threading.Thread(target=self.sgs_remote, args=(stb_name, stb_ip, rxid, command, delay))
                        thread.start()
                    elif protocol == 'rf':
                        self.rf_remote(com_port, remote, command, delay)

            except Exception as e:
                logging.error(f"Failed to process button press: {str(e)}")
                print(f"Failed to process button press: {e}")

    def is_ip_local(self, stb_name, stb_ip):
        logging.debug(f"Checking if IP {stb_ip} for STB {stb_name} is local.")
        try:
            stb_ip_address = ipaddress.ip_address(stb_ip)
            is_local = False
            #subnets = get_subnets_from_arp()
            is_local = ping_ip(stb_ip)
            logging.debug(f"Is {stb_ip} local? {is_local}")
        except ValueError as ve:
            logging.error(f"Invalid IP address {stb_ip}: {str(ve)}")
            self.output_text.insert(tk.END, f"Invalid IP address {stb_ip}: {str(ve)}\n")
            return False
        except Exception as e:
            logging.error(f"Error checking IP locality for {stb_ip}: {str(e)}")
            self.output_text.insert(tk.END, f"Error checking IP locality: {str(e)}\n")
            return False

        return is_local
        
    def sgs_remote(self, stb_name, stb_ip, rxid, button_id, delay):
        logging.debug(f"Sending SGS remote command to STB {stb_name} with IP {stb_ip}, RxID {rxid}, and button ID {button_id}")
        os.chdir(script_dir)
        stb_config = self.config_data['stbs'].get(stb_name, {})
        linux_pc = stb_config.get('linux_pc', 'default_linux_ip')
        command = get_sgs_codes(button_id, delay)
        lcmd = ["python", "sgs_remote.py", "-n", stb_name, command]
        rcmd = ["python", "sgs_remote.py", "-i", stb_ip, "-s", rxid, command]

        def run_command():
            try:
                if self.is_ip_local(stb_name, stb_ip):
                    logging.debug(f"Executing SGS command locally for STB {stb_name}.")
                    result = subprocess.run(lcmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output = result.stdout.decode() + result.stderr.decode()
                    self.output_text.insert(tk.END, f"SGS {stb_name} {output}")
                    self.output_text.see(tk.END)
                    if "Please enter PIN:" in output:
                        logging.info("PIN prompt detected.")
                        self.handle_pin_prompt(lcmd)
                else:
                    logging.info(f"STB {stb_name} is outside local network. Using SSH to reach {linux_pc}.")
                    self.ensure_ssh_connection(linux_pc)
                    if self.ssh_client and self.ssh_client.get_transport().is_active():
                        try:
                            stdin, stdout, stderr = self.ssh_client.exec_command(
                                f'cd ~/JAMboree/scripts && python3 sgs_remote.py -n {stb_name} \"{command}\"')
                            output = stdout.read().decode() + stderr.read().decode()
                            self.output_text.insert(tk.END, output)
                            self.output_text.see(tk.END)
                            if "Please enter PIN:" in output:
                                self.handle_pin_prompt(rcmd)
                        except paramiko.SSHException as e:
                            logging.error(f"SSH command execution failed for STB {stb_name}: {str(e)}")
                            self.output_text.insert(tk.END, f"Failed to execute remote command: SSH error: {str(e)}\n")
                            if "unhandled type 3 ('unimplemented')" in str(e):
                                self.output_text.insert(tk.END, "It seems the server does not support the requested operation.\n")
                        except Exception as e:
                            logging.error(f"Failed to execute remote command via SSH for STB {stb_name}: {str(e)}")
                            self.output_text.insert(tk.END, f"Failed to execute remote command: {str(e)}\n")
            except subprocess.CalledProcessError as e:
                logging.error(f"SGS remote command failed for STB {stb_name} with exit status {e.returncode}: {e.output.decode()}")
                self.output_text.insert(tk.END, f"SGS remote command failed with exit status {e.returncode}: {e.output.decode()}\n")
                self.output_text.see(tk.END)
            except Exception as e:
                logging.error(f"An error occurred during SGS remote execution for STB {stb_name}: {str(e)}")
                self.output_text.insert(tk.END, f"An error occurred during SGS remote execution: {str(e)}\n")
                self.output_text.see(tk.END)

        # Start the command in a new thread
        thread = threading.Thread(target=run_command)
        thread.start()
                                    
    def on_close(self):
        logging.info("Closing application and saving configuration.")
        self.save_config()
        if self.ssh_client:
            self.ssh_client.close()
        self.destroy()
        self.close_all_serial_connections()
        logging.info("Restarting JAMboree GUI.")
        JAMboree_gui().mainloop()  # Reopen the window

    def rf_remote(self, com_port, remote, button_id, delay):
        logging.debug(f"Sending RF remote command to COM port {com_port}, Remote {remote}, Button ID {button_id}, Delay {delay}")
        if button_id.lower() == 'live' or button_id.lower().startswith('lp'):
            delay = 1100
            button_id = button_id[2:] if button_id.lower().startswith('lp') else button_id

        try:
            delay = int(delay)
        except ValueError:
            logging.error(f"Invalid delay value: {delay}")
            return jsonify({'error': 'Invalid delay value'}), 400

        if delay < 80:
            delay = 80

        button_codes = get_button_codes(button_id)
        if not button_codes:
            logging.error(f"Button ID {button_id} not recognized.")
            return jsonify({'error': f'Button ID {button_id} not recognized'}), 404

        if not self.serial_connection or self.serial_connection.port != com_port:
            logging.warning(f"Port {com_port} closed. Trying to reconnect.")
            self.output_text.insert(tk.END, "Port closed: Trying to reconnect...\n")
            self.output_text.see(tk.END)
            self.open_serial_connection(com_port)
            time.sleep(1)
            if not self.serial_connection or not self.serial_connection.is_open:
                logging.error(f"Failed to open serial port {com_port}.")
                self.output_text.insert(tk.END, "Failed to open serial port. Please check the connection.\n")
                self.output_text.see(tk.END)
                return

        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = f"{button_codes['KEY_CMD']} {button_codes['KEY_RELEASE']}" if button_id != 'reset' else "reset"
                message = f"{remote} {command} {delay}\n".encode('utf-8')
                self.serial_connection.write(message)
                self.serial_connection.flush()
                time.sleep((delay + 30) / 1000.0)
                response = self.serial_connection.read_all().decode('utf-8').strip()
                logging.debug(f"RF command response: {response}")
                self.output_text.insert(tk.END, f"{response}\n")
                self.output_text.see(tk.END)
            except serial.SerialException as e:
                logging.error(f"Failed to send RF command: {str(e)}")
                self.output_text.insert(tk.END, f"Failed to send RF command: {str(e)}\n")
                self.output_text.see(tk.END)
                return f"Failed to send RF command: {str(e)}", 500

        return response, 200
			
    def check_channel(self):
        channel_check_file = 'channel_check.json'
        os.chdir(script_dir)    
        any_selected = False 
        
        if os.path.exists(channel_check_file):
            with open(channel_check_file, 'r') as file:
                channel_data = json.load(file)
        else:
            channel_data = {}
    
    
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():
                any_selected = True
                stb_name = self.stb_comboboxes[idx].get()  # Assume the combobox has the STB name
                cmd = f"python get_tuner_usage_v2.py -n \"{stb_name}\""
                print(f"Executing command: {cmd}")                
                try:
                    result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output = result.stdout.decode()
                    
                    if "Returned data:" in output:
                        data_str = output.split("Returned data: ")[1].split('Error:')[0].strip()
                        #print(f"data_str {data_str}")
                        data_tuple = ast.literal_eval(data_str)
                        if isinstance(data_tuple, tuple) and isinstance(data_tuple[0], dict):
                            data = data_tuple[0]
                            
                            tuners = data.get('tuner_usage_list', [])
                            channel_data[stb_name] = tuners
                            
                            for tuner in tuners:
                                title = tuner.get('title', '')
                                tuner_id = tuner.get('tuner', '')
                                if title:
                                    self.output_text.insert(tk.END, f"{stb_name} tuner {tuner_id} {title}\n")
                            self.output_text.see(tk.END)

                            
                            with open(channel_check_file, 'w') as file:
                                json.dump(channel_data, file, indent=4)
                                print("Channel data saved to 'channel_check.json'")
                            
                    
                except subprocess.CalledProcessError as e:
                    print(f"Command failed: {e.stderr}")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

    def check_multicast(self):
        channel_check_file = 'multicast_check.json'
        os.chdir(script_dir)
        any_selected = False
    
        if os.path.exists(channel_check_file):
            with open(channel_check_file, 'r') as file:
                channel_data = json.load(file)
        else:
            channel_data = {}
    
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():
                any_selected = True
                stb_name = self.stb_comboboxes[idx].get()  # Assume the combobox has the STB name
                cmd = f"python get_multicasts.py -n \"{stb_name}\" -v"
                print(f"Executing command: {cmd}")
                try:
                    result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output = result.stdout.decode()

                    # Store raw output for debugging purposes
                    #raw_data_key = f"{stb_name}_raw"
                    #channel_data[raw_data_key] = output

                    # Parse the output
                    if output:
                        tuners = []
                        lines = output.strip().split('\r')
                        tuner_data = {}
                        tuner_usage_data = {}
                        #self.output_text.insert(tk.END, f"{lines}\n")

                        for line in lines:
                            line = line.strip()
                            #self.output_text.insert(tk.END, f"reading: {line}\n")
                            if "response:" in line:
                                parts = line.split("response:", 1)
                                if len(parts) > 1:
                                    response_json = parts[1].strip()
                                    #self.output_text.insert(tk.END, f"found {line}\n")
                                    try:
                                        response_data = json.loads(response_json)
                                        if 'tuners' in response_data:
                                            tuner_data = response_data
                                        elif 'tuner_usage_list' in response_data:
                                            tuner_usage_data = response_data
                                    except json.JSONDecodeError as e:
                                        print(f"Error decoding JSON response: {e}")

                        # Combine tuner_data and tuner_usage_data
                        if tuner_data and tuner_usage_data:
                            for tuner in tuner_data.get('tuners', []):
                                usage = next((usage for usage in tuner_usage_data.get('tuner_usage_list', []) if usage['tuner'] == tuner['tuner_id']), None)
                                if usage:
                                    tuner.update(usage)
                                tuners.append(tuner)
                    
                        channel_data[stb_name] = tuners
                    
                        for tuner in tuners:
                            title = tuner.get('title', '')
                            tuner_id = tuner.get('tuner_id', '')
                            if title:  # Only print if title is present
                                addresses = ", ".join([multicast.get('address', '') for multicast in tuner.get('multicasts', [])])
                                self.output_text.insert(tk.END, f"{stb_name} tuner {tuner_id} {title} {addresses}\n")
                        self.output_text.see(tk.END)
                    
                        with open(channel_check_file, 'w') as file:
                            json.dump(channel_data, file, indent=4)
                            print("Multicast data saved to 'multicast_check.json'")
                    
                except subprocess.CalledProcessError as e:
                    print(f"Command failed: {e.stderr}")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")
                    
    def authorizations(self):
        authorizations_file = 'authorizations.txt'
        os.chdir(script_dir)    
        any_selected = False 
        
        if os.path.exists(authorizations_file):
            with open(authorizations_file, 'r') as file:
                authorizations = json.load(file)
        else:
            authorizations = {}
    
    
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():
                any_selected = True
                stb_name = self.stb_comboboxes[idx].get()  # Assume the combobox has the STB name
                cmd = f"python get_authorization.py -n \"{stb_name}\""
                print(f"Executing command: {cmd}")                
                try:
                    result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output = result.stdout.decode()
                    
                    
                    lines = output.split('\n')
                    auths = []
                    for line in lines:
                        if 'right' in line or 'authorization' in line:
                            auths.append(line.strip())
                            
                    # Update the dictionary for this STB
                    authorizations[stb_name] = auths
                    self.output_text.insert(tk.END, f"{stb_name}: {'; '.join(auths)}\n")
                    self.output_text.see(tk.END)
                    print(f"Data for {stb_name} updated successfully.")
            
                except subprocess.CalledProcessError as e:
                    # Handle command execution errors
                    self.output_text.insert(tk.END, f"Error for {stb_name}: {e.stderr.decode()}\n")
                    self.output_text.see(tk.END)
                except Exception as e:
                    # Handle other exceptions
                    self.output_text.insert(tk.END, f"An error occurred: {str(e)}\n")
                    self.output_text.see(tk.END)
                    
        # Save updated data back to the file
        with open(authorizations_file, 'w') as file:
            json.dump(authorizations, file, indent=4)
            print("authorizations saved to 'authorizations.txt'")

    
        if not any_selected:
            self.output_text.insert(tk.END, "No STB selected!\n")
            self.output_text.see(tk.END)
            
    class SGSPairing:
        def __init__(self, output_text, pin_entry):
            self.output_text = output_text
            self.pin_entry = pin_entry
            self.proc = None


        def sgs_pair(self, stb_name, stb_ip, rxid):
            os.chdir(script_dir)

            def run_pairing_process():
                try:
                    cmd = ["python", "sgs_pair.py", "-s", rxid, "-i", stb_ip, "-v"]
                    self.output_text.insert(tk.END, f"{cmd}\n")
                    self.output_text.see(tk.END)
                    try:
                        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
                        full_output = ""
                        while True:
                            output = self.proc.stdout.readline()
                            if output.strip():
                                self.output_text.insert(tk.END, f"Output: {output}")
                                self.output_text.see(tk.END)
                                full_output += output
    
                            if "Please enter PIN:" in output:
                                self.output_text.insert(tk.END, "PIN prompt detected. Waiting for user to enter PIN...\n")
                                self.output_text.see(tk.END)
                                self.pin_entry.config(state=tk.NORMAL)
                                return  # Exit the loop, waiting for PIN entry
    
                            if self.proc.poll() is not None:
                                break
    
                        self.process_full_output(full_output, rxid)

                    except Exception as e:
                        self.output_text.insert(tk.END, f"Failed to start pairing process: {str(e)}\n")
                        self.output_text.see(tk.END)

                except Exception as e:
                    self.output_text.insert(tk.END, f"Error with command setup: {str(e)}\n")
                    self.output_text.see(tk.END)

            threading.Thread(target=run_pairing_process).start()

        def submit_pin(self):
            pin = self.pin_entry.get()
            if self.proc:
                try:
                    self.proc.stdin.write(pin + '\n')
                    self.proc.stdin.flush()
                    self.output_text.insert(tk.END, "PIN sent successfully.\n")
                    self.output_text.see(tk.END)

                    full_output = ""
                    while True:
                        output = self.proc.stdout.readline()
                        if output.strip():
                            self.output_text.insert(tk.END, f"Output: {output}")
                            self.output_text.see(tk.END)
                            full_output += output

                        if self.proc.poll() is not None:
                            break

                    self.process_full_output(full_output, self.entries[0].get())

                except Exception as e:
                    self.output_text.insert(tk.END, f"Failed to send PIN {pin}: {str(e)}\n")
                    self.output_text.see(tk.END)

        def process_full_output(self, full_output, rxid):
            cred_match = re.search(r"\((\S+):(\S+)\)", full_output)
            if cred_match:
                login_val = cred_match.group(1)
                passwd_val = cred_match.group(2)
                self.update_config(rxid, login_val, passwd_val)
            else:
                self.output_text.insert(tk.END, "Failed to capture login and password. Check the response.\n")
                self.output_text.see(tk.END)

        def update_config(self, rxid, login, passwd):
            os.chdir(script_dir)    
            try:
                with open(self.config_file, 'r') as file:
                    config_data = json.load(file)

                # Update the specific STB's login and password
                updated = False
                for stb_name, stb_info in config_data["stbs"].items():
                    if stb_info.get('stb', '')[:11] == rxid:                    
                        stb_info["lname"] = login
                        stb_info["passwd"] = passwd
                        stb_info["prod"] = "true"
                        updated = True
                        print(f"Credentials updated for {stb_name} with RxID {rxid}.")
                        break

                if not updated:
                    print(f"No STB with rxid {rxid} found. No updates made.")
    
                with open(self.config_file, 'w') as file:
                    json.dump(config_data, file, indent=4)
            except Exception as e:
                print(f"Failed to update configuration for {stb_name}: {e}")
                
@app.route('/remote')
def home():
    return render_template('JAMboRemote.html')
    
@app.route('/base.txt')
def base_txt():
    os.chdir(script_dir)
    return send_from_directory('base.txt')
    


@app.route('/settops', methods=['GET', 'POST'], strict_slashes=False)
def settops():
    return render_template('settops.html')


@app.route('/base', methods=['GET', 'POST'], strict_slashes=False)
def handle_base():
    if request.method == 'GET':
        with open(config_file, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    
    elif request.method == 'POST':
        new_data = request.json
        with open(config_file, 'w') as f:
            json.dump(new_data, f, indent=4)
        return jsonify({"success": True})    

@app.route('/55/<remote>/<button_id>/<delay>', methods=['GET', 'POST'], strict_slashes=False)
def handle_55_remote(remote, button_id, delay):
    os.chdir(script_dir)
    remote = remote.lstrip('0')  # Strip leading zeros from the remote value

    try:
        with open(config_file, 'r') as file:
            config_data = json.load(file)
        
        com_port = config_data.get('com_port')
        if not com_port:
            return jsonify({'error': 'COM port not found', 'timestamp': datetime.now(timezone.utc).isoformat()}), 404
        
        response, status = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
        return jsonify({'response': response, 'timestamp': datetime.now(timezone.utc).isoformat()}), status
    except Exception as e:
        return jsonify({'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}), 500
    
@app.route('/rf/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'], strict_slashes=False)
def handle_54_remote(remote, stb_name, button_id, delay):
    # Call the instance method from the Flask app
    response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
    return jsonify({'response': response})

        
@app.route('/auto/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'], strict_slashes=False)
@app.route('/auto/<remote>/<stb_name>/<button_id>/<delay>', methods=['GET', 'POST'], strict_slashes=False)
def handle_auto_remote(remote, stb_name, button_id, delay):
    # Call the instance method from the Flask app
    os.chdir(script_dir)
    try:
        delay = int(delay)  # Ensure delay is an integer
        with open(config_file, 'r') as file:  # Adjust the file path as necessary
            config_data = json.load(file)

        # Find the STB details
        stb_details = config_data['stbs'].get(stb_name)
        if not stb_details:
            return jsonify({'error': 'STB not found'}), 404

        stb_ip = stb_details.get('ip')
        rxid = stb_details.get('stb')
        com_port = stb_details.get('com_port')
        protocol = stb_details.get('protocol')
        remote = stb_details.get('remote')

        if not all([stb_ip, rxid]):
            return jsonify({'error': 'Incomplete STB details'}), 400
            
        if protocol == 'RF':
            response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
        
        elif protocol == 'SGS':
            response = app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, button_id, delay)
        
        return jsonify({'response': response, 'timestamp': datetime.now(timezone.utc).isoformat()})

    except FileNotFoundError:
        return jsonify({'error': 'Configuration file not found'}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to decode the configuration file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sgs/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'], strict_slashes=False)
def handle_sgs_remote(remote, stb_name, button_id, delay):
    os.chdir(script_dir)
    try:
        delay = int(delay)  # Ensure delay is an integer
        with open(config_file, 'r') as file:  # Adjust the file path as necessary
            config_data = json.load(file)

        # Find the STB details
        stb_details = config_data['stbs'].get(stb_name)
        if not stb_details:
            return jsonify({'error': 'STB not found'}), 404

        stb_ip = stb_details.get('ip')
        rxid = stb_details.get('stb')
        #print("Discovered IPs:", stb_ip)

        if not all([stb_ip, rxid]):
            return jsonify({'error': 'Incomplete STB details'}), 400

        # Assuming `sgs_remote` is properly defined in your controller
        response = app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, button_id, delay)
        return jsonify({'response': response})

    except FileNotFoundError:
        return jsonify({'error': 'Configuration file not found'}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to decode the configuration file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/triggered/<date>/<machine_name>/<stb_name>/<category_id>/<event_id>', methods=['GET', 'POST'], strict_slashes=False)
def triggered(date, machine_name, stb_name, category_id, event_id):
    
    try:
        with open(config_file, 'r') as file:
            config_data = json.load(file)

        stb_details = config_data['stbs'].get(stb_name)
        if not stb_details:
            return jsonify({'error': 'STB not found'}), 404

        stb_ip = stb_details.get('ip')
        protocol = stb_details.get('protocol')
        rxid = stb_details.get('stb')
        com_port = stb_details.get('com_port')
        delay = "80"
        remote = stb_details.get('remote')
        
        #print(f"stb_ip {stb_ip} protocol {protocol} ")
        if protocol == 'RF':
            #print("RF")
            app.config['controller'].rf_remote(com_port, remote, 'info', delay)
            app.config['controller'].rf_remote(com_port, remote, 'input', delay)
            app.config['controller'].rf_remote(com_port, remote, 'back', delay)
        if protocol == 'SGS':
            #print("SGS")
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'info', delay)
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'input', delay)
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'back', delay)
        
        
        # Load linked logs
        linked_logs_file = 'linkedlogs.json'  # Update with the correct path if needed
        with open(linked_logs_file, 'r') as logs_file:
            linked_logs = json.load(logs_file)

        # Find file IDs with the matching event_id
        file_ids = [log['id'] for log in linked_logs if log.get('event_id') == event_id]
        file_id_str = ','.join(map(str, file_ids)) 
        print(event_id)

        if not file_ids:
            return jsonify({'error': 'No matching logs found for event_id'}), 404

        upload(stb_name, file_id_str, ccshare)  # Use the correct upload destination
        #app.config['controller'].mark_logs(stb_name)
        print(stb_name)

        return jsonify({'status': 'Upload triggered', 'file_ids': file_ids}), 200

    except FileNotFoundError:
        return jsonify({'error': 'Configuration file not found'}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to decode the configuration file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


fetcher = JAMboree_gui()


@app.route('/54/<remote>/<button_id>', methods=['GET', 'POST'], strict_slashes=False)
def handle_54_remote_defaultdelay(remote, button_id):
    # Call the instance method from the Flask app
    response = app.config['controller'].rf_remote(com_port, remote, button_id, "80")
    return jsonify({'0response': response})
    
@app.route('/sgs/<remote>/<button_id>', methods=['GET', 'POST'], strict_slashes=False)
def handle_sgs_remote_defaultdelay(remote, button_id):
    # Call the instance method from the Flask app
    response = app.config['controller'].sgs_remote(remote, button_id, "80")
    return jsonify({'0response': response})
    
@app.route('/get-stb-list')
def get_stb_list():
    try:
        with open(config_file, 'r') as file:
            data = json.load(file)
            stbs = data.get("stbs", {})
            filtered_stbs = {
                stb_name: stb_details for stb_name, stb_details in stbs.items()
            }
            return jsonify({"stbs": filtered_stbs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/update-stb-selection', methods=['POST'])
def update_stb_selection():
    try:
        data = request.get_json()  # Parse the JSON data
        stbName = data['stbName']
        selectedId = data['selectedId']
        isSelected = data['isSelected']

        # Assume a function update_stb_config that updates your configuration
        update_result = update_stb_config(stbName, selectedId, isSelected)

        return jsonify({'success': True, 'message': 'STB selection updated successfully'})

    except Exception as e:
        # Return an error in JSON format
        return jsonify({'error': str(e)}), 500

def update_stb_config(stbName, selectedId, isSelected):
    # Here, implement the logic to update your configuration file or database
    # This is just a placeholder
    return True


@app.route('/apps')
def index():
    return render_template('dayJAM.html')

@app.route('/cc_share_apps', methods=['GET', 'POST'], strict_slashes=False)
def populate_file_list(self):
    self.file_listbox.delete(0, tk.END)  # Clear the listbox before populating
    apps_list_file = 'apps_list.json'
    try:
        linux_pc = self.get_linux_pc_from_config()
        credentials = load_credentials()
        username = credentials['username']
        password = credentials['password']

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        sftp = ssh.open_sftp()

        file_list = sftp.listdir_attr(self.remote_path)
        sorted_files = sorted(file_list, key=lambda x: x.st_mtime, reverse=True)
            
        apps_list = []
            
        for file in sorted_files:
            if file.filename.endswith('tgz'):
                file_date = datetime.fromtimestamp(file.st_mtime).strftime('%Y-%m-%d')
                file_entry = {"filename": file.filename, "date": file_date}
                apps_list.append(file_entry)
                self.file_listbox.insert(tk.END, f"{file_date} - {file.filename}")
                    
        with open(apps_list_file, 'w') as json_file:
            json.dump(apps_list, json_file, indent=4)

        sftp.close()
        ssh.close()
        self.update_output(f"File list saved to {apps_list_file}.")
    except Exception as e:
        self.update_output(f"Failed to populate file list: {e}")

@app.route('/api/apps', methods=['GET'])
def get_apps_list():
    try:
        with open(apps_list_file, 'r') as json_file:
            apps_list = json.load(json_file)
        return jsonify(apps_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_app', methods=['POST'])
def load_app():
    logging.debug("Received request to load app.")
    data = request.json
    selected_file = data.get('app')
    selected_stb = data.get('stb')
    logging.debug(f"Selected app: {selected_file}, Selected STB: {selected_stb}")

    if not selected_file or not selected_stb:
        logging.error("App or STB not selected.")
        return jsonify({'error': 'App or STB not selected'}), 400

    try:
        # Load configuration
        with open(config_file, 'r') as file:
            config_data = json.load(file)
            stbs = config_data.get('stbs', {})
            stb_info = stbs.get(selected_stb)
            if not stb_info:
                logging.error(f"STB {selected_stb} not found in configuration.")
                return jsonify({'error': f"STB {selected_stb} not found in configuration"}), 404

            stb_ip = stb_info.get('ip')
            linux_pc = stb_info.get('linux_pc')
            logging.debug(f"STB IP: {stb_ip}, Linux PC: {linux_pc}")

            if not stb_ip:
                logging.error(f"Failed to find IP for STB: {selected_stb}")
                return jsonify({'error': f"Failed to find IP for STB: {selected_stb}"}), 404

        # Load credentials
        credentials = load_credentials()
        username = credentials.get('username')
        password = credentials.get('password')
        logging.debug(f"Loaded credentials for user: {username}")

        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        sftp = ssh.open_sftp()
        logging.info(f"Connected to Linux PC: {linux_pc}")

        # Safely process the selected file name
        if ' - ' in selected_file:
            app_filename = selected_file.split(' - ')[1]
        else:
            app_filename = selected_file
            logging.warning(f"Unexpected file format for selected_file: {selected_file}. Using full string as app filename.")

        cc_share = f"/ccshare/linux/c_files/signed-browser-applications/internal/{app_filename}"
        local_apps = os.path.join(apps_dir, app_filename)
        linux_pc_dir = f'/home/{username}/stbmnt/apps/'
        linux_pc_app = os.path.join(linux_pc_dir, app_filename)

        logging.debug(f"App filename: {app_filename}, CC Share Path: {cc_share}, Local Apps Path: {local_apps}, Linux PC App Path: {linux_pc_app}")

        # Ensure the local apps directory exists
        if not os.path.exists(apps_dir):
            os.makedirs(apps_dir)
            logging.info(f"Created local apps directory: {apps_dir}")

        # Download the app if not already available locally
        if not os.path.exists(local_apps):
            logging.info(f"Downloading {app_filename} from CC Share.")
            sftp.get(cc_share, local_apps)
        else:
            logging.info(f"{app_filename} already exists locally, skipping download.")

        # Ensure the Linux PC directory exists
        try:
            sftp.chdir(linux_pc_dir)
            logging.info(f"Changed to Linux PC directory: {linux_pc_dir}")
        except IOError:
            logging.info(f"Creating directory on Linux PC: {linux_pc_dir}")
            ssh.exec_command(f"mkdir -p {linux_pc_dir}")

        # Upload the app to the Linux PC if it does not already exist there
        try:
            sftp.stat(linux_pc_app)
            logging.info(f"App already exists on Linux PC: {linux_pc_app}")
        except FileNotFoundError:
            logging.info(f"Uploading {app_filename} to Linux PC.")
            sftp.put(local_apps, linux_pc_app)

        sftp.close()
        ssh.close()
        logging.info(f"App {app_filename} loaded successfully onto {linux_pc}.")
        
        # Determine whether to run commands locally or over SSH
        if app.config['controller'].is_ip_local(stbs, stb_ip):
            #run_commands_local(stb_ip, app_filename)
            run_commands_over_ssh(linux_pc, username, password, stb_ip, app_filename)
        else:
            run_commands_over_ssh(linux_pc, username, password, stb_ip, app_filename)

        return jsonify({'status': 'App successfully prepared'})

    except Exception as e:
        logging.error(f"Error during app load: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
def run_commands_local(stb_ip, app):
    logging.debug("Starting run_commands_local function.")
    logging.debug(f"Parameters received - STB IP: {stb_ip}, App: {app}")

    try:
        tnet_local = 'tnet.jam'

        logging.debug(f"Local tnet.jam path: {tnet_local}")

        # Command to be executed locally
        command = f"expect {tnet_local} {stb_ip} apps {app}"
        logging.info(f"Running: {command}")

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if output:
            logging.info(f"Output from tnet command:\n{output.decode()}")
        if error:
            logging.error(f"Error from tnet command:\n{error.decode()}")

    except Exception as e:
        logging.error(f"Failed to execute commands locally: {e}")
    finally:
        logging.info("Stopping any music playback.")
        pygame.mixer.music.stop()

        
def run_commands_over_ssh(linux_pc, username, password, stb_ip, app):
    logging.debug("Starting run_commands_over_ssh function.")
    logging.debug(f"Parameters received - Linux PC: {linux_pc}, Username: {username}, STB IP: {stb_ip}, App: {app}")

    try:
        logging.info(f"Attempting to SSH into {linux_pc}.")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        logging.info(f"SSH connection established with {linux_pc}.")

        linux_pc_stbmnt = f'/home/{username}/stbmnt'
        tnet_remote_path = f"{linux_pc_stbmnt}/tnet.jam"
        tnet_local = 'tnet.jam'

        logging.debug(f"Remote tnet.jam path: {tnet_remote_path}, Local tnet.jam path: {tnet_local}")

        # Using SFTP to check and upload the tnet.jam file
        sftp = ssh.open_sftp()

        try:
            logging.info(f"Uploading tnet.jam to {linux_pc}:{tnet_remote_path}.")
            sftp.put(tnet_local, tnet_remote_path)
            logging.debug(f"tnet.jam uploaded successfully to {tnet_remote_path}.")
        except FileNotFoundError:
            logging.error(f"tnet.jam not found locally or unable to upload to {tnet_remote_path}.")
            raise

        sftp.close()

        # Command to be executed on the remote Linux PC
        command = f"expect {tnet_remote_path} {stb_ip} apps {app}"
        logging.info(f"Running command on {linux_pc}: {command}")

        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            logging.info(f"Output from tnet command:\n{output}")
        if error:
            logging.error(f"Error from tnet command:\n{error}")

        ssh.close()
        logging.info("SSH connection closed.")

    except Exception as e:
        logging.error(f"Failed to execute commands over SSH: {e}")
    finally:
        logging.info("Stopping any music playback.")
        pygame.mixer.music.stop()

@app.route('/hostname')
def hostname():
    return jsonify(hostname=socket.gethostname())
        

def get_linux_pc_from_config(stbs):
    with open(config_file, 'r') as file:
        config_data = json.load(file)
    linux_pc = next(iter(config_data['stbs'].values()))['linux_pc']  # Fetch any linux_pc from the config
    return linux_pc

if __name__ == '__main__':
    # app = JAMboree_gui()
    # app.mainloop()
    app.config['controller'] = fetcher
    #app.config['controller'] = JAMboree_gui()
    app.config['controller'].mainloop()
