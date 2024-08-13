
####5/6/2024  added Live function in rf remote
#### 5/12/2024 added unpair button *enter blood code to enable
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
#from video_ui import VideoUI
import ast
from PIL import Image, ImageTk

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for the entire Flask app

# Append the directory containing sgs_lib to the system path
script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary

sys.path.append(script_dir)  ## add this in front of sub process: "  os.chdir(script_dir)  "
config_file = 'base.txt'
credentials_file = 'credentials.json'

class JAMboree_gui(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.ssh_client = None  
        computer_name = socket.gethostname()  # Get the computer's hostname
        self.title(f'{computer_name} - JAMboree')  # Set window title with computer name
        self.geometry('825x900')  # Adjust the size as needed        
        self.thin_geometry = '420x900'
        self.mid_geometry = '825x900'
        self.width = 1100
        self.height = 900
        self.full_geometry = f"{self.width}x{self.height}"
        
        self.ssh_username_var = tk.StringVar()  # No default value
        self.ssh_password_var = tk.StringVar()  # No default value
        
        # Theme Colors
        self.bg_color = "#222222"  # Dark grey for background
        self.fg_color = "#ffffff"  # White for text
        self.btn_bg = "#555555"  # Lighter grey for buttons
        self.entry_bg = "#555555"  # Lighter grey for entries
        self.btn_fg = "#ffffff"  # White text for buttons
        
        # Load and resize the background image
        self.bg_image = Image.open("time-warp.jpg").resize((self.width, self.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        # Create a canvas and set the background image
        self.canvas = tk.Canvas(self, width=self.width, height=self.height)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor='nw')

        # Create a frame to hold the widgets
        self.frame = tk.Frame(self.canvas, bg='')  # Set background color to empty string
        self.frame.place(x=0, y=0, width=self.width, height=self.height)  # Adjust the placement as needed

        #self.canvas.create_window((0, 0), window=self.frame, anchor='nw')

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
        self.unpair_sequence = ['Left', 'Down', 'Left', 'Right', 'Down', 'Right', 'Left', 'Left', 'Right', 'Right']  # was self.key_sequence
        self.debug_sequence = ['Left', 'Left', 'Right', 'Right', 'Up', 'Down', 'Up', 'Down']
        self.current_sequence = []
        self.unpair_btn = None  # This will hold the button widget once created
        self.load_credentials()  # Load credentials on startup

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def __del__(self):
        self.close_all_serial_connections()
        if self.ssh_client:
            self.ssh_client.close()  # Ensure the SSH connection is closed when the instance is deleted
        super().__del__()

    def setup_ui(self):
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
        
        self.credentials_frame = ttk.Frame(self)
        self.credentials_frame.pack(fill='both', expand=True)

        # Start Flask app in a separate thread
        self.flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False))
        self.flask_thread.start()
        self.extra_column_visible = False  # Control visibility of the master column
        self.thin_mode_active = False  # Control visibility of the master column

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
        
        # Configure columns 5 to 10
        #column_widths = {8: 15, 9: 10, 10: 5}
        #for col, width in column_widths.items():
            #self.frame.grid_columnconfigure(col, minsize=width)
            #self.frame.grid_columnconfigure(col, weight=1)
            #print(f"Configured column {col} with width {width}")

        self.pin_entry = ttk.Entry(self.frame, style='TEntry', width=8)
        self.pin_entry.grid(row=19, column=1, columnspan=1, sticky='ew')
        self.pin_submit_btn = ttk.Button(self.frame, text="PIN", command=self.submit_pin)
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
            ' - ': ('1', '2'),    
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
        
        pair_btn = ttk.Button(self.frame, text="SGS Pair", command=lambda: self.process_button_press(None, 'pair'), style='TButton')
        pair_btn.grid(row=19, column=0, sticky='ew', padx=2, pady=2)
        


        self.apply_dark_theme(self.frame)
        self.refresh()

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
        try:
            if self.ssh_client is None:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                self.ssh_client.connect(linux_pc, username=self.ssh_username_var.get(), password=self.ssh_password_var.get())
                self.output_text.insert(tk.END, "Connected to proxy. \n")
        except paramiko.AuthenticationException:
            self.output_text.insert(tk.END, "Authentication failed, please check your username or password.\n")
        except paramiko.SSHException as e:
            self.output_text.insert(tk.END, f"SSH error: {str(e)}\n")
        except Exception as e:
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
        if key_name in ['Left', 'Right', 'Up', 'Down']:  # Only track arrow keys
            self.current_sequence.append(key_name)
            print(f"Current sequence: {self.current_sequence}")  # Debugging output
            
            # Check if the current sequence matches the prefix of the target sequence
            if (self.current_sequence != self.debug_sequence[:len(self.current_sequence)] and
                self.current_sequence != self.unpair_sequence[:len(self.current_sequence)]):
                self.current_sequence = []  # Reset if any mismatch
                print("Sequence mismatch - Resetting")  # Debugging output
                
            if self.current_sequence == self.unpair_sequence:
                self.show_unpair_button()
                self.current_sequence = []  # Reset if any mismatch
                
                
            if self.current_sequence == self.debug_sequence:
                self.open_DebugGUI()
                self.current_sequence = []  # Reset if any mismatch

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
        print("Unpairing...")
        for idx, var in enumerate(self.checkbox_vars):
            if var.get():  # Check if the checkbox for the STB is selected
                remote = str(idx + 1)
                self.rf_remote(self.com_port, remote, 'sat', 3100)  # Press and hold 'sat' button
                self.after(3100, lambda: self.rf_remote(self.com_port, remote, 'pair_down', 80))  # Press 'pair_down'
                self.after(6200, lambda: self.rf_remote(self.com_port, remote, 'pair_up', 80))  # Press 'pair_up' after previous delay
        self.after(6200, self.hide_unpair_button)
        
    def mark_logs(self):
        
        print("marking...")        
        self.process_button_press(None, '13')
        self.after(3000, lambda: self.process_button_press(None, '38'))
        self.after(5000, lambda: self.process_button_press(1000, '11'))
        
    def update_related_fields(self, event):
        selected_index = event.widget.current()
        # Assuming that all comboboxes have the same index for related items
        self.stb_name_cb.current(selected_index)
        self.stb_rxid_cb.current(selected_index)
        self.stb_ip_cb.current(selected_index)
        self.save_config()

    def update_remote_value(self, event):
        new_remote = self.new_remote_entry.get().strip()
        if new_remote and new_remote != 'enter new #':
            selected_stb_name = self.stb_name_cb.get()  # Assume you have a Combobox for STB names
            if selected_stb_name:
                self.update_remote_in_config(selected_stb_name, new_remote)
                self.refresh()  # Refresh the GUI
            self.new_remote_entry.delete(0, tk.END)
            self.entry_focus_out(None)  # Reset the placeholder text
            
    def update_remote_in_config(self, stb_name, new_remote):    
        os.chdir(script_dir)
        with open(self.config_file, 'r') as file:
            config_data = json.load(file)
        if stb_name in self.config_data['stbs']:
            config_data['stbs'][stb_name]['remote'] = new_remote  # Update the remote value
            with open(config_file, 'w') as file:
                json.dump(config_data, file, indent=4)
               
            print(f"Updated remote for {stb_name} to {new_remote}")
    
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

    def update_linux_pc_history(self, event=None):
        # Update history list and dropdown if the new entry is not already in the list
        new_entry = self.linux_pc_var.get()
        if new_entry and new_entry not in self.linux_pc_history:
            self.linux_pc_history.append(new_entry)
            self.linux_pc_combobox['values'] = self.linux_pc_history
        self.save_config()
   
    def check_all(self):
        """Toggle all checkboxes based on the state of the 'Check All' checkbox."""
        is_checked = self.all_var.get()
        for var in self.checkbox_vars:
            var.set(is_checked)
        self.save_config()

    def set_all_protocols(self, event):
        """Set all comboboxes to the selected protocol."""
        protocol = self.protocol_var.get()
        for combo in self.comboboxes:
            combo.set(protocol)
        self.save_config()

    def start_timer(self, button_id):
        self.button_press_times[button_id] = int(time.time() * 1000)
        
    def on_com_select(self, event=None):
        selected_com_port = self.com_select.get().split(' ')[-1].strip('()')
        if selected_com_port and (selected_com_port != self.com_port):
            self.com_port = selected_com_port  # Update the current COM port
            self.open_serial_connection(self.com_port)
            
    def open_serial_connection(self, com_port):
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
                self.output_text.insert(tk.END, f" Opened: {com_port}\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
            except serial.SerialException as e:
                self.output_text.insert(tk.END, f"Failed to open serial port: {str(e)}\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
                self.serial_connection = None


    def close_serial_connection(self, com_port):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.close_all_serial_connections()

    def close_all_serial_connections(self):
        for com_port, connection in self.serial_connections.items():
            if connection and connection.is_open:
                connection.close()
                self.output_text.insert(tk.END, f"Closed serial port: {com_port}\n")
                self.output_text.see(tk.END)

    def save_config(self):
        os.chdir(script_dir)
        try:
            with open(self.config_file, 'r') as file:
                config_data = json.load(file)

            # Reset all entries to "is_recent": "false"
            for stb in config_data["stbs"].values():
                stb["is_recent"] = "false"
    
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
            if self.com_port:
                config_data["com_port"] = self.com_port


            with open(self.config_file, 'w') as file:
                json.dump(config_data, file, indent=4)
            
            #print("Configuration saved.")
            self.config_data = config_data
        except Exception as e:
            print("Failed to save configuration:", e)

    def load_config(self):
        self.stb_by_remote = {}
        os.chdir(script_dir)
        try:
            with open(self.config_file, 'r') as file:
                self.config_data = json.load(file)
                com_port = self.config_data.get("com_port", None)  # Load the COM port safely

            
        
                # Check and refresh available COM ports
                available_ports = self.find_serial_ports()
                print(f"available ports: {available_ports}")
                self.com_select['values'] = [f"{name}" for name in available_ports]

                # Attempt to open the serial connection
                if com_port:
                    self.com_port = com_port
                    self.open_serial_connection(com_port)  # Safely open the connection with error handling
                    
                stbs_discovered = [stb for stb in self.config_data.get("stbs", {}).values() if str(stb.get('remote')) == "0"]
                self.stb_name_cb['values'] = [name for name, stb in self.config_data["stbs"].items() if str(stb.get('remote')) == "0"]
                self.stb_rxid_cb['values'] = [stb['stb'] for stb in stbs_discovered]  # Correct key for RxID
                self.stb_ip_cb['values'] = [stb['ip'] for stb in stbs_discovered] 
            
                if stbs_discovered:
                    # Automatically select the first entry by default (if it exists)
                    self.stb_name_cb.current(0)
                    self.stb_rxid_cb.current(0)
                    self.stb_ip_cb.current(0)
                    # No need to set 'new_remote_entry' as it is for user input to change 'remote'


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
        except Exception as e:
            print("Failed to load config:", e)


    def get_combobox_values(self, saved_value, stbs, key):
        values = list({data[key] for data in stbs.values() if key in data})  # Use a set to remove duplicates
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        return values
        
        
    def get_combobox_values_with_available_ports(self, saved_value, available_ports):
        values = available_ports[:]
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        return values
        
    def find_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        friendly_ports = [port.description.split(' ')[-1].strip('()') for port in ports]
        #print("port: ", ports)
        #print("friendly_ports: ", friendly_ports)
        return friendly_ports
        #return ports

    def refresh(self):
        self.load_config()

    def find_sgs(self):
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
    

    def process_button_press(self, event, button_id, stb_name=None):
        start_time = self.button_press_times.get(button_id, int(time.time() * 1000))
        end_time = int(time.time() * 1000)
        delay = end_time - start_time
        #button_name = next(name for name, id in self.buttons.items() if id == button_id)
        button_name = next((name for name, ids in self.buttons.items() if ids[0] == button_id), "Unknown")
        self.save_config()
        print("button_name:", button_name)
        if button_id == 'reset':
            all_com_ports = self.find_serial_ports()
            # Send the reset command to each COM port
            for com_port in all_com_ports:
                self.rf_remote(com_port, '1', button_id, delay)  # Assumes '1' is a valid remote ID for all cases
        
        elif button_id == 'pair':
            # Handle SGS Pairing
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if details.get('selected')}
                updated = False 
                for stb_name, stb_details in selected_stbs.items():
                    rxid = stb_details.get('stb', '')[:11]
                    stb_ip = stb_details.get('ip', '')
                    self.sgs_pair(stb_name, stb_ip, rxid)
                    updated = True
                if updated:
                    print("Configurations updated successfully.")
                else:
                    print("No STBs were selected for pairing.")

            except Exception as e:
                self.output_text.insert(tk.END, f"Failed to process SGS Pair: {e}\n")
                self.output_text.see(tk.END)
            
        else:
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if details.get('selected')}
                for stb_name, stb_details in selected_stbs.items():
                    rxid = stb_details.get('stb', '')[:11]  # Assume receiver ID is first 11 characters
                    stb_ip = stb_details.get('ip', '')
                    protocol = stb_details.get('protocol', '').lower()
                    com_port = stb_details.get('com_port', '')
                    remote = stb_details.get('remote', '')
                    command = button_name 
                    #print("stb_name:", stb_name)
                    if protocol.lower() == 'sgs':
                        thread = threading.Thread(target=self.sgs_remote, args=(stb_name, stb_ip, rxid, command, delay))
                        #print("thread:", thread)
                        thread.start()
                    elif protocol.lower() == 'rf':
                        self.rf_remote(com_port, remote, command, delay)
                        
            except Exception as e:
                print(f"Failed to process button press: {e}")
                            
    def update_ssh_username_history(self, event=None):
        # Update history list and dropdown if the new entry is not already in the list
        new_entry = self.ssh_username_var.get()
        if new_entry and new_entry not in self.ssh_username_history:
            self.ssh_username_history.append(new_entry)
            self.ssh_username_combobox['values'] = self.ssh_username_history

    def is_ip_local(self, stb_name, stb_ip):
        #self.output_text.insert(tk.END, f"Checking if IP {stb_ip} is local...\n")
        try:
            stb_ip_address = ipaddress.ip_address(stb_ip)
            is_local = False
            subnets = get_subnets_from_arp()
            is_local = any(stb_ip_address in subnet for subnet in subnets)
            #is_local = ping_ip(stb_ip)
            #print(f'pinging: {stb_ip}')
            #self.output_text.insert(tk.END, f"Its not in subnets {stb_name} \n")
            '''
            if not is_local:
                # If not on the same subnet, check if it is reachable via ping
                try:
                    # Ping the IP address
                    if platform.system().lower() == "windows":
                        ping_command = ['ping', '-n', '1', '-w', '400', str(stb_ip_address)]
                    else:
                        ping_command = ['ping', '-c', '1', '-W', '1', str(stb_ip_address)]
                        
                    result = subprocess.run(ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    #self.output_text.insert(tk.END, f"pinging {stb_name} {result}")
                    if result.returncode == 0:
                        is_local = True
                    else:
                        is_local = False
                except Exception as ping_exception:
                    self.output_text.insert(tk.END, f"Ping test failed for {stb_ip}: {str(ping_exception)}\n")
                    is_local = False
'''
        except ValueError as ve:
            self.output_text.insert(tk.END, f"Invalid IP address {stb_ip}: {str(ve)}\n")
            return False
        except Exception as e:
            self.output_text.insert(tk.END, f"Error checking IP locality: {str(e)}\n")
            return False

        return is_local

    def sgs_remote(self, stb_name, stb_ip, rxid, button_id, delay):
        os.chdir(script_dir)
        stb_config = self.config_data['stbs'].get(stb_name, {})
        linux_pc = stb_config.get('linux_pc', 'default_linux_ip')  # Fetch specific linux_pc or default
        #print(f'linux pc {linux_pc}')
        command = get_sgs_codes(button_id, delay)
        lcmd = ["python", "sgs_remote.py", "-n", stb_name, command]
        rcmd = ["python", "sgs_remote.py", "-i", stb_ip, "-s", rxid, command]
        
        def run_command():
            try:
                if self.is_ip_local(stb_name, stb_ip):
                    result = subprocess.run(lcmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=    subprocess.PIPE)
                    output = result.stdout.decode() + result.stderr.decode()
                    self.output_text.insert(tk.END, f"SGS {stb_name} {output}")
                    self.output_text.see(tk.END)
                    if f"Please enter PIN:" in output:
                        print('enter PIN below')
                        self.handle_pin_prompt(lcmd)
                else:
                    self.output_text.insert(tk.END, f"Reaching outside your network: {stb_name} \n")
                    self.output_text.see(tk.END)
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
                            self.output_text.insert(tk.END, f"Failed to execute remote command: SSH error: {str(e)}\n")
                            if "unhandled type 3 ('unimplemented')" in str(e):
                                self.output_text.insert(tk.END, "It seems the server does not support the     requested operation.\n")
                        except Exception as e:
                            self.output_text.insert(tk.END, f"Failed to execute remote command: {str(e)}\n")
            except subprocess.CalledProcessError as e:
                self.output_text.insert(tk.END, f"SGS remote command failed with exit status {e.returncode}: {e.    output.decode()}\n")
                self.output_text.see(tk.END)
            except Exception as e:
                self.output_text.insert(tk.END, f"An error occurred during SGS remote execution: {str(e)}\n")
                self.output_text.see(tk.END)

        # Start the command in a new thread
        thread = threading.Thread(target=run_command)
        thread.start()

                                    
    def on_close(self):
            self.save_config()
            if self.ssh_client:
                self.ssh_client.close()
            self.destroy()
            self.close_all_serial_connections()
            JAMboree_gui().mainloop()  # Reopen the window
          
    def run_sgs_remote(self, cmd, stb_name, timeout=10):
        try:
            result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            self.output_text.insert(tk.END, f"SGS {stb_name} ")
            self.output_text.insert(tk.END, f"{result.stdout.decode()}")
            self.output_text.see(tk.END)
        #except subprocess.TimeoutExpired:
            #self.output_text.insert(tk.END, f"Timeout: Command took too long and was aborted.\n")
            #self.output_text.see(tk.END)
        except subprocess.CalledProcessError as e:
            self.output_text.insert(tk.END, f"Error: {e.stderr.decode()}\n")
            self.output_text.see(tk.END)

    def rf_remote(self, com_port, remote, button_id, delay):
        #com_port = self.com_port_comboboxes[idx].get()

        if button_id.lower() == ('live'):
            delay = 1100        
        if button_id.lower().startswith('lp'):
            delay = 1100
        # Strip 'LP' from button_id
            button_id = button_id[2:]
        try:
            delay = int(delay)  # Ensure delay is an integer
        except ValueError:
            return jsonify({'error': 'Invalid delay value'}), 400
        if delay < 80 :
            delay = 80
        button_codes = get_button_codes(button_id)
        #self.handle_command(button_id, int(delay))
        self.output_text.insert(tk.END, f"RF {com_port} {remote} : {button_id} {delay} ")
        self.output_text.see(tk.END)
        if not button_codes:
            return jsonify({'error': f'Button ID {button_id} not recognized'}), 404
        if not self.serial_connection or self.serial_connection.port != com_port:
            self.output_text.insert(tk.END, "Port closed: Trying to reconnect...\n")
            self.output_text.see(tk.END)  # Scroll to the bottom
            self.open_serial_connection(com_port)
            time.sleep(1)
            if not self.serial_connection or not self.serial_connection.is_open:
                self.output_text.insert(tk.END, "Failed to open serial port. Please check the connection.\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
                return
        if self.serial_connection and self.serial_connection.is_open:        
            if button_id == 'reset':
                cmd = "reset"		
            else: 
                KEY_CMD = button_codes['KEY_CMD']
                KEY_RELEASE = button_codes['KEY_RELEASE']
                cmd = f"{KEY_CMD} {KEY_RELEASE}"
            try:
                message = f"{remote} {cmd} {delay}\n".encode('utf-8')
                self.serial_connection.write(message)
                self.serial_connection.flush()
                time.sleep((delay + 30) / 1000.0)
                response = self.serial_connection.read_all().decode('utf-8').strip()
                self.output_text.insert(tk.END,f"{response}\n")
                self.output_text.see(tk.END) 
                
            except serial.SerialException as e:
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
                   
    def sgs_pair(self, stb_name, stb_ip, rxid):     
        os.chdir(script_dir)    
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
                        break
                    if self.proc.poll() is not None:
                        break
                    
                cred_match = re.search(r"\((\S+):(\S+)\)", full_output)
                if cred_match:
                    login_val = cred_match.group(1)
                    passwd_val = cred_match.group(2)
                    self.update_config(rxid, login_val, passwd_val)
                else:
                    self.output_text.insert(tk.END, "Failed to capture login and password. Check the response.\n")
                    self.output_text.see(tk.END)
                
            except Exception as e:
                self.output_text.insert(tk.END, f"Failed to start pairing process: {str(e)}\n")
                self.output_text.see(tk.END)  # Scroll to the bottom
        except Exception as e:
            self.output_text.insert(tk.END, f"Error with command setup: {str(e)}\n")
            self.output_text.see(tk.END)  # Scroll to the bottom
    
    def handle_pin_prompt(self, cmd):
        self.output_text.insert(tk.END, "PIN prompt detected. Waiting for user to enter PIN...\n")
        self.output_text.see(tk.END)
        self.proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)       

    def submit_pin(self):
        pin = self.pin_entry.get()
        
        if self.proc :
            try:
                self.proc.stdin.write(pin + '\n')
                self.proc.stdin.flush()
                self.output_text.insert(tk.END, "PIN sent successfully.\n")
                self.output_text.see(tk.END)

                # Collect full response after sending the PIN
                full_response = ""
                while True:
                    response = self.proc.stdout.readline()
                    if response == '' and self.proc.poll() is not None:
                        break
                    if response.strip():
                        full_response += response
                        self.output_text.insert(tk.END, response)
                        self.output_text.see(tk.END)

                # Extract credentials from the response
                login_match = re.search(r"login:\s+(\S+)", full_response)
                passwd_match = re.search(r"passwd:\s+(\S+)", full_response)
                if login_match and passwd_match:
                    login_val = login_match.group(1)
                    passwd_val = passwd_match.group(1)
                    self.update_config(self.entries[0].get(), login_val, passwd_val)
                else:
                    self.output_text.insert(tk.END, "Failed to capture login and password. Check the output above.\n")
                    self.output_text.see(tk.END)
            except Exception as e:
                self.output_text.insert(tk.END, f"Failed to send {pin}: {str(e)}\n")
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

@app.route('/')
def home():
    return render_template('JAMboree.html')
    
@app.route('/base.txt')
def base_txt():
    os.chdir(script_dir)
    return send_from_directory('base.txt')
    

@app.route('/55/<remote>/<button_id>/<delay>', methods=['GET', 'POST'])
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
    
@app.route('/rf/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'])
def handle_54_remote(remote, stb_name, button_id, delay):
    # Call the instance method from the Flask app
    response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
    return jsonify({'response': response})
       
@app.route('/auto/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'])
def handle_auto_remote(remote, stb_name, button_id, delay):
    # Call the instance method from the Flask app
    #response = app.config['controller'].rf_remote(remote, button_id, delay)
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
        #print("Discovered IPs:", stb_ip)

        if not all([stb_ip, rxid]):
            return jsonify({'error': 'Incomplete STB details'}), 400
            
        if protocol == 'RF':
            response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
        
        if protocol == 'SGS':
            response = app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, button_id, delay)
        # Assuming `sgs_remote` is properly defined in your controller
        #response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
        #response = app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, button_id, delay)
        return jsonify({'response': response})

    except FileNotFoundError:
        return jsonify({'error': 'Configuration file not found'}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to decode the configuration file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sgs/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'])
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


@app.route('/triggered/<date>/<machine_name>/<stb_name>/<category_id>/<event_id>', methods=['GET', 'POST'])
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


@app.route('/54/<remote>/<button_id>', methods=['GET', 'POST'])
def handle_54_remote_defaultdelay(remote, button_id):
    # Call the instance method from the Flask app
    response = app.config['controller'].rf_remote(com_port, remote, button_id, "80")
    return jsonify({'0response': response})
    
@app.route('/sgs/<remote>/<button_id>', methods=['GET', 'POST'])
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

if __name__ == '__main__':
    # app = JAMboree_gui()
    # app.mainloop()
    app.config['controller'] = fetcher
    #app.config['controller'] = JAMboree_gui()
    app.config['controller'].mainloop()
