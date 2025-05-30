from scp import SCPClient
import sys
import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime, timedelta, timezone
import subprocess
import glob
import queue
import ftplib
import requests
import threading
import shutil
import ipaddress
import paramiko
import sched
import psycopg2
import time
from threading import Thread
import serial.tools.list_ports
import serial
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response
from flask_cors import CORS
from commands import get_button_codes, get_sgs_codes, get_button_number
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from get_stb_list import *
import socket
from debug_gui import DebugGUI
from debug_gui import *
import logging
import ast
from PIL import Image, ImageTk
from pathlib import Path

# Set up logging
logging.basicConfig(filename='debugJam.log', level=logging.DEBUG)
logging.debug('JAMboree script started.')

paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.ERROR)  # Only show warnings and errors for Paramiko

# Suppress DEBUG logs from urllib3
urllib3_logger = logging.getLogger("urllib3")
urllib3_logger.setLevel(logging.WARNING)  # You can also use ERROR if you want to suppress warnings too

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for the entire Flask app

# Append the directory containing sgs_lib to the system path
script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary
sys.path.append(script_dir)

config_file = 'base.txt'
credentials_file = 'credentials.txt'
apps_list_file = 'apps_list.txt'
software_list_file = 'software.txt'
press_count = 0  # Global counter to track button presses


##### This class represents a graphical user interface (GUI) built using the Tkinter library for controlling STBs (Set-Top Boxes) and managing remote commands.

class JAMboree_gui(tk.Tk):

    def __init__(self, *args, **kwargs):
        #### Inputs: Optional arguments passed when initializing the Tkinter window.
        #### Outputs: Initializes the GUI with default values, sets up widgets, and connects to required services.
        #### Purpose: Initializes the window, GUI layout, SSH configurations, serial connections, and prepares the environment.
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
        self.output_text = tk.Text(self.frame, height=10, width=100, bg=self.bg_color, fg=self.fg_color,
                                   insertbackground=self.fg_color)
        self.output_text.grid(row=18, column=0, columnspan=10, pady=5, padx=10, sticky='w')
        logging.debug('UI elements initialized.')

        self.unpair_sequence = ['Left', 'Down', 'Left', 'Right', 'Down', 'Right', 'Left', 'Left', 'Right',
                                'Right']  # was self.key_sequence
        self.debug_sequence = ['Left', 'Left', 'Right', 'Right', 'Up', 'Down', 'Up', 'Down']
        self.current_sequence = []
        self.unpair_btn = None  # This will hold the button widget once created
        self.load_credentials()  # Load credentials on startup

        logging.debug('Initial setup complete.')

        self.pin_entry = ttk.Entry(self.frame, style='TEntry', width=8)
        self.pin_entry.grid(row=19, column=1, columnspan=1, sticky='ew')

        self.sgs_pairing_instance = self.SGSPairing(self.output_text, self.pin_entry)

        self.command_queue = queue.Queue()
        self.start_command_processor()

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
        #### Inputs: None.
        #### Outputs: UI elements like buttons, labels, and comboboxes are added to the GUI.
        #### Purpose: Constructs the interface elements for interacting with the STBs and other system components.

        logging.debug('Setting up UI components.')
        self.configure(bg=self.bg_color)  # Set the background color of the root window

        style = ttk.Style()
        style.theme_use('clam')  # This theme allows color customization
        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color,
                        insertcolor=self.fg_color)  # Correct style for Entry
        style.configure("TButton", background=self.btn_bg, foreground=self.btn_fg, relief='flat')  # Button style
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)  # Label style
        style.configure("TCombobox", fieldbackground=self.entry_bg, background=self.btn_bg, foreground=self.fg_color)
        style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)])
        style.map('TCombobox', selectbackground=[('readonly', self.entry_bg)])
        style.map('TCombobox', selectforeground=[('readonly', self.fg_color)])
        style.configure("TCheckbutton", background=self.bg_color, foreground=self.fg_color,
                        focuscolor=style.configure(".")["background"])
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
        ttk.Label(self.frame, text='STB Name', style='TLabel').grid(row=0, column=4, pady=(2, 0), sticky='ew')
        ttk.Label(self.frame, text='STB RxID', style='TLabel').grid(row=0, column=5, pady=(2, 0), sticky='ew')
        ttk.Label(self.frame, text='STB IP', style='TLabel').grid(row=0, column=6, pady=(2, 0), sticky='ew')
        ttk.Label(self.frame, text='Joey''s Master', style='TLabel').grid(row=0, column=10)
        ttk.Label(self.frame, text='Linux IP', style='TLabel').grid(row=0, column=9)
        ttk.Label(self.frame, text='COM Port', style='TLabel').grid(row=0, column=8)

        # Check all checkbox
        self.all_var = tk.BooleanVar()
        self.check_all_btn = ttk.Checkbutton(self.frame, text="All", variable=self.all_var, command=self.check_all,
                                             style="TCheckbutton")
        self.check_all_btn.grid(row=0, column=3, sticky='ew')

        self.bind_all('<Key>', self.track_keys)

        # Protocol dropdown for all
        self.protocol_var = tk.StringVar()
        self.protocol_all_combo = ttk.Combobox(self.frame, values=['RF', 'SGS'], state='readonly',
                                               textvariable=self.protocol_var, width=8)
        self.protocol_all_combo.grid(row=0, column=7, sticky='w', padx=2, pady=(1, 1))
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

            master_combo.grid(row=i + 1, column=10, padx=3, pady=(1, 1))
            linux_pc_combo.grid(row=i + 1, column=9, padx=3, pady=(1, 1))
            com_port_combo.grid(row=i + 1, column=8, padx=3, pady=(1, 1))

            # master_combo.grid_remove()  # Hide initially
            # linux_pc_combo.grid_remove()  # Hide initially
            # com_port_combo.grid_remove()  # Hide initially

            self.master_comboboxes.append(master_combo)
            self.linux_pc_comboboxes.append(linux_pc_combo)
            self.com_port_comboboxes.append(com_port_combo)

            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.frame, text='#' + str(i + 1), variable=var, style="TCheckbutton")
            chk.grid(row=i + 1, sticky='ew', column=3, padx=2)
            self.checkbox_vars.append(var)
            self.checkboxes.append(chk)

            stb_combo = ttk.Combobox(self.frame, style='TCombobox', width=12)
            remote_index = str(i + 1)
            stb_combo.grid(row=i + 1, column=4)
            stb_combo.bind("<<ComboboxSelected>>", lambda event, idx=i: self.on_stb_select(idx))
            self.stb_comboboxes.append(stb_combo)

            for j in range(5, 7):  # Three entries: Name, RXID, IP
                entry = ttk.Entry(self.frame, style='TEntry')
                entry.grid(row=i + 1, column=j, padx=2)
                self.entries.append(entry)

            combo = ttk.Combobox(self.frame, values=['RF', 'SGS'], state='readonly', width=5)
            combo.grid(row=i + 1, sticky='ew', column=7)
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
        self.new_remote_entry = ttk.Entry(self.frame, foreground="grey", width=5)
        self.new_remote_entry.insert(0, "#")
        self.new_remote_entry.grid(row=17, column=7)
        self.new_remote_entry.bind('<FocusIn>', self.entry_focus_in)
        self.new_remote_entry.bind('<FocusOut>', self.entry_focus_out)
        self.new_remote_entry.bind('<Return>', self.update_remote_value)

        # Bind comboboxes to a method that updates other fields
        self.stb_name_cb.bind("<<ComboboxSelected>>", self.update_related_fields)
        self.stb_rxid_cb.bind("<<ComboboxSelected>>", self.update_related_fields)
        self.stb_ip_cb.bind("<<ComboboxSelected>>", self.update_related_fields)

        # self.authorizations_btn = ttk.Button(self.frame, text="Get Auth's", command=self.authorizations, style='TButton')
        # self.authorizations_btn.grid(row=20, column=4, padx=2, pady=2)

        # Button to toggle Master Column visibility
        self.toggle_master_btn = ttk.Button(self.frame, text="Show Extras", command=self.toggle_master_column,
                                            style='TButton')
        self.toggle_master_btn.grid(row=19, column=4, padx=2)

        self.com_select = ttk.Combobox(self.frame, state="readonly")
        self.com_select.grid(row=1, columnspan=2, column=0, sticky='ew', padx=2)
        self.com_select.bind("<<ComboboxSelected>>", self.on_com_select)

        refresh_btn = ttk.Button(self.frame, text="Refresh", command=self.refresh, style='TButton')
        refresh_btn.grid(row=0, column=0, sticky='ew', padx=2, pady=2)

        find_sgs_btn = ttk.Button(self.frame, text="find_sgs", command=self.find_sgs, style='TButton')
        find_sgs_btn.grid(row=0, column=1, sticky='ew', padx=2, pady=2)

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
            self.bind_all(f"<Control-{key}>",
                          lambda event, bid=button_id: self.process_button_press(event, bid))  # This binds Ctrl + key

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

        pair_btn = ttk.Button(self.frame, text="pair", command=lambda: self.process_button_press(None, 'pair'),
                              style='TButton')
        pair_btn.grid(row=19, column=0, sticky='ew', padx=2, pady=2)

        pair_btn = ttk.Button(self.frame, text="SGS Pair", command=lambda: self.SGSPairing.sgs_pair(), style='TButton')
        pair_btn.grid(row=20, column=0, sticky='ew', padx=2, pady=2)

        self.apply_dark_theme(self.frame)
        self.refresh()
        logging.debug('UI components setup complete.')

    def apply_dark_theme(self, parent):
        #### Inputs: parent - a Tkinter widget to which styles are applied.
        #### Outputs: Modifies the color scheme of UI elements to follow a dark theme.
        #### Purpose: Applies a dark theme to all widgets inside the parent widget.

        for widget in parent.winfo_children():
            widget_type = widget.winfo_class()
            if widget_type in ["TButton", "TLabel", "TEntry", "TCombobox"]:
                widget.configure(style=widget_type)  # Apply the respective style
            elif isinstance(widget, tk.Text):
                widget.configure(bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
            if widget.winfo_children():
                self.apply_dark_theme(widget)

    def load_credentials(self):
        #### Inputs: None.
        #### Outputs: Loads stored SSH credentials from a file into GUI fields.
        #### Purpose: Load SSH credentials for Linux PC connections from a configuration file.

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
            # self.close_and_reopen()
        else:
            # Not in thin mode, need to hide widgets from start_column onwards
            for widget in self.grid_slaves():
                widget_col = int(widget.grid_info().get("column", 0))
                if widget_col >= start_column or widget_col in columns_to_toggle:
                    # print(f"Hiding widget at column {widget_col}")
                    widget.grid_remove()  # Remove the widget from the grid
            self.thin_mode_active = True  # Toggle the state
            print("Switched to thin mode")

        # Update layout and resize window after toggling widget states
        self.update_idletasks()
        if self.thin_mode_active:
            self.geometry(self.thin_geometry)  # Smaller, predefined size for thin mode
        else:
            self.geometry(self.full_geometry)  # Reset to full geometry

    def send_reset_and_sat(self, com_port):
        self.rf_remote(com_port, '1', 'reset', 80)
        for remote in range(1, 16):
            self.rf_remote(str(remote), 'sat', 80)
        print("Sent reset and SAT to all remotes")

    def schedule_reset_and_sat(self):
        self.send_reset_and_sat(self.com_port)
        self.scheduler.enter(600, 1, self.schedule_reset_and_sat)

    def ensure_ssh_connection(self, linux_pc):
        #### Inputs: linux_pc - The IP or hostname of the Linux PC to connect to.
        #### Outputs: Establishes an SSH connection.
        #### Purpose: Ensures an SSH connection is active with a remote Linux PC.

        logging.debug(f"Ensuring SSH connection to {linux_pc}.")
        try:
            if self.ssh_client is None:
                logging.debug("Creating new SSH client instance.")
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                logging.debug("Establishing SSH connection.")
                self.ssh_client.connect(linux_pc, username=self.ssh_username_var.get(),
                                        password=self.ssh_password_var.get())
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
                # Thread(target=self.old_get_dev_logs, args=(linux_pc, stb_ip, hopper_rid, ssh_username)).start()

        if not any_selected:
            self.output_text.insert(tk.END, "No STB selected!\n")
            self.output_text.see(tk.END)

    def get_dev_logs(self, linux_pc, stb_ip, hopper_rid, ssh_username, retry=False):
        #### Inputs:
        #### linux_pc: Hostname/IP of Linux PC.
        #### stb_ip: IP address of the STB.
        #### hopper_rid: Remote Identifier for the STB.
        #### ssh_username: SSH username.
        #### retry: Whether to retry fetching logs.
        #### Outputs: Retrieves logs from an STB.
        #### Purpose: Executes commands via SSH to gather logs from STBs and transfer them to local/remote servers.

        date = datetime.now().strftime('%Y-%m-%d')
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
        ftp_directory = f'smplogs/{log_folder}'
        studio_dir = f'/smplogs/{log_folder}'

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
                    f'expect stbmnt/tnet.jam {stb_ip}  {ftp_directory}',
                    f'cp /var/mnt/MISC_HD/nal_0.cur nal_0.cur \r'
                    f'cp /var/mnt/MISC_HD/esosal_log/stb_lightning/stb_lightning.0 stb_lightning.0 \r'
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
                esosal_folders = [folder.strip() for folder in esosal_output.split('\n') if
                                  folder.strip() and not folder.startswith('total')]

                # Log the esosal folders for debugging
                self.output_text.insert(tk.END, f"Esosal folders: {esosal_output}\n")
                self.output_text.see(tk.END)

                # Copy files from esosal_log
                for folder in esosal_folders:
                    command = f'cp /var/mnt/MISC_HD/esosal_log/{folder}/{folder}.0 {folder}.0'
                    run_command(command)

                # Get the list of folders in '/var/mnt/MISC_HD/joey_logs/'
                joey_output = run_command('ls -1 /var/mnt/MISC_HD/joey_logs/')
                joey_folders = [folder.strip() for folder in joey_output.split('\n') if
                                folder.strip() and not folder.startswith('total')]

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

                # run_command(f'scp /home/diship/stbmnt/smplogs/* {studio_username}@{studio}/smplogs/ ')

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
                    # scp.send(f'{ftp_directory}/{file_name}',  preserve_times=True, progress=progress)

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

        tk.Label(password_window, text=f"Linux PC: {linux_pc}\nUsername: {ssh_username}").grid(row=0, column=0,
                                                                                               columnspan=2, padx=5,
                                                                                               pady=5)
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
                self.after(6200, lambda: self.rf_remote(self.com_port, remote, 'pair_up',
                                                        80))  # Press 'pair_up' after previous delay
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
        # logging.debug(f"Updating related fields based on selected index: {selected_index}")
        # Assuming that all comboboxes have the same index for related items
        self.stb_name_cb.current(selected_index)
        self.stb_rxid_cb.current(selected_index)
        self.stb_ip_cb.current(selected_index)
        # logging.info(f"Related fields updated for index: {selected_index}")
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
                return [stb_name for stb_name, stb_details in config_data['stbs'].items() if
                        stb_details.get('model') != 'Joey']
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

                print(
                    f"Updated master for {selected_joey} to {selected_master}, IP: {master_data['ip']}, RID: {master_data['stb']}")
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
                # logging.debug(f"Set is_recent to false for STB.")

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
                    # logging.debug(f"Updated STB {stb_name} in config.")

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
        # logging.debug("Loading configuration.")
        try:
            with open(self.config_file, 'r') as file:
                self.config_data = json.load(file)
                # logging.debug("Configuration file loaded.")

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

            stbs_discovered = [stb for stb in self.config_data.get("stbs", {}).values() if
                               str(stb.get('remote')) == "0"]
            self.stb_name_cb['values'] = [name for name, stb in self.config_data["stbs"].items() if
                                          str(stb.get('remote')) == "0"]
            self.stb_rxid_cb['values'] = [stb['stb'] for stb in stbs_discovered]  # Correct key for RxID
            self.stb_ip_cb['values'] = [stb['ip'] for stb in stbs_discovered]
            # logging.debug(f"STBs discovered: {stbs_discovered}")

            if stbs_discovered:
                # Automatically select the first entry by default (if it exists)
                self.stb_name_cb.current(0)
                self.stb_rxid_cb.current(0)
                self.stb_ip_cb.current(0)
                logging.info("Automatically selected first STB entry.")

            for idx in range(len(self.checkbox_vars)):
                remote_index = str(idx + 1)
                relevant_stbs = [name for name, data in self.config_data["stbs"].items() if
                                 data.get("remote") == remote_index]
                sorted_stbs = sorted(relevant_stbs, key=lambda x: self.config_data["stbs"][x].get("is_recent", "false"),
                                     reverse=True)
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
                    self.linux_pc_comboboxes[idx]['values'] = self.get_combobox_values(data.get("linux_pc", ''),
                                                                                       self.config_data["stbs"],
                                                                                       "linux_pc")
                    self.linux_pc_comboboxes[idx].set(data.get("linux_pc", ''))
                    self.master_comboboxes[idx]['values'] = self.get_combobox_values(data.get("master_stb", ''),
                                                                                     self.config_data["stbs"],
                                                                                     "master_stb")
                    self.master_comboboxes[idx].set(data.get("master_stb", ''))
                    self.com_port_comboboxes[idx]['values'] = self.get_combobox_values_with_available_ports(
                        data.get("com_port", ''), available_ports)
                    self.com_port_comboboxes[idx].set(data.get("com_port", ''))
                    # logging.info(f"Loaded configuration for STB: {stb_name}.")
        except Exception as e:
            logging.error(f"Failed to load configuration: {str(e)}")

    def get_combobox_values(self, saved_value, stbs, key):
        values = list({data[key] for data in stbs.values() if key in data})  # Use a set to remove duplicates
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        # logging.debug(f"Combobox values for {key} generated: {values}")
        return values

    def get_combobox_values_with_available_ports(self, saved_value, available_ports):
        values = available_ports[:]
        if saved_value in values:
            values.remove(saved_value)
        values.insert(0, saved_value)
        # logging.debug(f"Combobox values with available ports generated: {values}")
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

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if
                                 details.get('selected')}
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

                selected_stbs = {name: details for name, details in config_data['stbs'].items() if
                                 details.get('selected')}
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
            # subnets = get_subnets_from_arp()
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
        logging.debug(
            f"Sending SGS remote command to STB {stb_name} with IP {stb_ip}, RxID {rxid}, and button ID {button_id}")
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
                    result = subprocess.run(lcmd, shell=True, check=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
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
                                self.output_text.insert(tk.END,
                                                        "It seems the server does not support the requested operation.\n")
                        except Exception as e:
                            logging.error(f"Failed to execute remote command via SSH for STB {stb_name}: {str(e)}")
                            self.output_text.insert(tk.END, f"Failed to execute remote command: {str(e)}\n")
            except subprocess.CalledProcessError as e:
                logging.error(
                    f"SGS remote command failed for STB {stb_name} with exit status {e.returncode}: {e.output.decode()}")
                self.output_text.insert(tk.END,
                                        f"SGS remote command failed with exit status {e.returncode}: {e.output.decode()}\n")
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
        logging.debug(
            f"Sending RF remote command to COM port {com_port}, Remote {remote}, Button ID {button_id}, Delay {delay}")
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
            time.sleep(0.1)
            if not self.serial_connection or not self.serial_connection.is_open:
                logging.error(f"Failed to open serial port {com_port}.")
                self.output_text.insert(tk.END, "Failed to open serial port. Please check the connection.\n")
                self.output_text.see(tk.END)
                return

        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = f"{button_codes['KEY_CMD']} {button_codes['KEY_RELEASE']}" if button_id != 'reset' else "reset"
                message = f"{remote} {command} {delay}\n".encode('utf-8')
                attempt = 0
                max_attempts = 2  # Original attempt + one retry after reset

                while attempt < max_attempts:
                    self.serial_connection.write(message)
                    self.serial_connection.flush()
                    time.sleep((delay + 50) / 1000.0)
                    response_bytes = self.serial_connection.read_all()
                    logging.debug(f"Raw bytes received from serial port: {response_bytes}")

                    # Attempt to decode the response
                    try:
                        response = response_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError as e_utf8:
                        logging.warning(f"UTF-8 decoding failed: {e_utf8}. Trying 'latin-1'.")
                        try:
                            response = response_bytes.decode('latin-1').strip()
                        except UnicodeDecodeError as e_latin1:
                            logging.error(f"'latin-1' decoding failed: {e_latin1}. Displaying raw hex.")
                            response = ' '.join(f'{b:02X}' for b in response_bytes)

                    logging.debug(f"RF command response: {response}")
                    self.output_text.insert(tk.END, f"{response}\n")
                    self.output_text.see(tk.END)

                    if "Timeout waiting for acknowledgment" in response:
                        logging.warning("Timeout detected, sending reset command and retrying.")
                        # Send 'reset\n' to the serial connection
                        reset_message = 'reset\n'.encode('utf-8')
                        # reset_message = 'reset'
                        self.serial_connection.write(reset_message)
                        self.serial_connection.flush()
                        time.sleep(5)  # Wait briefly after reset
                        attempt += 1  # Increment attempt count to retry the original message
                    else:
                        break  # Exit loop if no timeout

                else:
                    logging.error("Command failed after retrying with reset.")
                    return f"Failed to send RF command after reset.", 500

            except serial.SerialException as e:
                logging.error(f"Failed to send RF command: {str(e)}")
                self.output_text.insert(tk.END, f"Failed to send RF command: {str(e)}\n")
                self.output_text.see(tk.END)
                return f"Failed to send RF command: {str(e)}", 500

        return response, 200

    def start_command_processor(self):
        threading.Thread(target=self.process_commands, daemon=True).start()

    def process_commands(self):
        while True:
            stb_name, button_id, action = self.command_queue.get()
            self._send_command(stb_name, button_id, action)
            self.command_queue.task_done()

    def dart(self, stb_name, button_id, action):
        # Enqueue the command
        self.command_queue.put((stb_name, button_id, action))
        return jsonify({'status': 'Command queued'}), 200

    def _send_command(self, stb_name, button_id, action):
        with open(config_file, 'r') as file:
            config_data = json.load(file)

        stb_details = config_data['stbs'].get(stb_name)
        if not stb_details:
            logging.error(f"STB {stb_name} not found")
            return

        com_port = stb_details.get('com_port')
        remote = stb_details.get('remote')

        logging.debug(
            f"Sending RF remote command to COM port {com_port}, Remote {remote}, Button ID {button_id}, Action {action}")

        button_number = get_button_number(button_id)
        if not button_number:
            logging.error(f"Button ID {button_id} not recognized.")
            return

        if not self.serial_connection or self.serial_connection.port != com_port:
            logging.warning(f"Port {com_port} closed. Trying to reconnect.")
            self.open_serial_connection(com_port)
            time.sleep(0.1)
            if not self.serial_connection or not self.serial_connection.is_open:
                logging.error(f"Failed to open serial port {com_port}.")
                return

        if self.serial_connection and self.serial_connection.is_open:
            try:
                message = f"{remote} {button_number} {action}\n".encode('utf-8')
                self.serial_connection.write(message)
                self.serial_connection.flush()

                response = self.serial_connection.read_all().decode('utf-8').strip()
                logging.debug(f"RF command response: {response}")
                return response

            except serial.SerialException as e:
                logging.error(f"Failed to send RF command: {str(e)}")
                return f"Failed to send RF command: {str(e)}"

    def check_channel(self):
        channel_check_file = 'channel_check.txt'
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
                        # print(f"data_str {data_str}")
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
                                print("Channel data saved to 'channel_check.txt'")


                except subprocess.CalledProcessError as e:
                    print(f"Command failed: {e.stderr}")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

    def check_multicast(self):
        channel_check_file = 'multicast_check.txt'
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
                    # raw_data_key = f"{stb_name}_raw"
                    # channel_data[raw_data_key] = output

                    # Parse the output
                    if output:
                        tuners = []
                        lines = output.strip().split('\r')
                        tuner_data = {}
                        tuner_usage_data = {}
                        # self.output_text.insert(tk.END, f"{lines}\n")

                        for line in lines:
                            line = line.strip()
                            # self.output_text.insert(tk.END, f"reading: {line}\n")
                            if "response:" in line:
                                parts = line.split("response:", 1)
                                if len(parts) > 1:
                                    response_json = parts[1].strip()
                                    # self.output_text.insert(tk.END, f"found {line}\n")
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
                                usage = next((usage for usage in tuner_usage_data.get('tuner_usage_list', []) if
                                              usage['tuner'] == tuner['tuner_id']), None)
                                if usage:
                                    tuner.update(usage)
                                tuners.append(tuner)

                        channel_data[stb_name] = tuners

                        for tuner in tuners:
                            title = tuner.get('title', '')
                            tuner_id = tuner.get('tuner_id', '')
                            if title:  # Only print if title is present
                                addresses = ", ".join(
                                    [multicast.get('address', '') for multicast in tuner.get('multicasts', [])])
                                self.output_text.insert(tk.END, f"{stb_name} tuner {tuner_id} {title} {addresses}\n")
                        self.output_text.see(tk.END)

                        with open(channel_check_file, 'w') as file:
                            json.dump(channel_data, file, indent=4)
                            print("Multicast data saved to 'multicast_check.txt'")

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
        def __init__(self, output_text, pin_entry, stb_name=None):
            self.output_text = output_text
            self.pin_entry = pin_entry
            self.stb_name = stb_name
            self.proc = None
            self.entries = [pin_entry]  # Initialize entries with pin_entry or other relevant UI elements

        def sgs_pair(self, stb_name, stb_ip, rxid):
            os.chdir(script_dir)
            self.stb_name = stb_name

            def run_pairing_process():
                try:
                    cmd = ["python", "sgs_pair.py", "-s", rxid, "-i", stb_ip, "-v"]
                    self.output_text.insert(tk.END, f"{cmd}\n")
                    self.output_text.see(tk.END)
                    try:
                        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE, text=True, bufsize=1,
                                                     universal_newlines=True)
                        full_output = ""
                        while True:
                            output = self.proc.stdout.readline()
                            if output.strip():
                                self.output_text.insert(tk.END, f"Output: {output}")
                                self.output_text.see(tk.END)
                                full_output += output

                            if "Please enter PIN: " in output:
                                self.output_text.insert(tk.END,
                                                        "PIN prompt detected. Waiting for user to enter PIN...\n")
                                self.output_text.see(tk.END)
                                self.pin_entry.config(state=tk.NORMAL)
                                return  # Exit the loop, waiting for PIN entry

                            if self.proc.poll() is not None:
                                break

                        # Check if the process ended and PIN was not needed
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

                    time.sleep(2)

                    full_output = ""
                    while True:
                        output = self.proc.stdout.readline()
                        if output.strip():
                            self.output_text.insert(tk.END, f"Output: {output}")
                            self.output_text.see(tk.END)
                            full_output += output

                        if self.proc.poll() is not None:
                            break

                    # Handle output after PIN is sent
                    self.process_full_output(full_output, self.entries[0].get())

                except Exception as e:
                    self.output_text.insert(tk.END, f"Failed to send PIN {pin}: {str(e)}\n")
                    self.output_text.see(tk.END)

        def process_full_output(self, full_output, rxid):
            # Debug print the full output for troubleshooting
            self.output_text.insert(tk.END, f"Full Output after PIN submission: {full_output}\n")
            self.output_text.see(tk.END)
            try:
                # Look for the JSON response in the full output
                response_start = full_output.find("{")
                response_end = full_output.rfind("}") + 1

                if response_start != -1 and response_end != -1:
                    json_response = full_output[response_start:response_end]
                    data = json.loads(json_response)

                    # Capture the name and password from the JSON data
                    login_val = data.get("name")
                    passwd_val = data.get("passwd")

                    if login_val and passwd_val:
                        self.update_config(rxid, login_val, passwd_val)
                    else:
                        self.output_text.insert(tk.END,
                                                "Failed to capture login and password. They might be missing in the response.\n")
                        self.output_text.see(tk.END)
                else:
                    self.output_text.insert(tk.END, "Failed to find JSON response in the output.\n")
                    self.output_text.see(tk.END)

            except json.JSONDecodeError as e:
                self.output_text.insert(tk.END, f"JSON decoding failed: {str(e)}\n")
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


def _deep_merge(target: dict, incoming: dict):
    """
    Recursively merge `incoming` into `target`:
     - if both target[k] and incoming[k] are dicts, merge recursively
     - else overwrite target[k] with incoming[k]
    """
    for k, v in incoming.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            _deep_merge(target[k], v)
        else:
            target[k] = v

@app.route('/base', methods=['GET', 'POST'], strict_slashes=False)
def handle_base():
    if request.method == 'GET':
        # Just return current config
        with open(config_file, 'r') as f:
            data = json.load(f)
        return jsonify(data)

    # POST: merge incoming JSON into existing config
    incoming = request.get_json(force=True)

    # load existing, or start empty if missing
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # if the existing config has a top-level "stbs" dict
    # and the incoming keys look like individual STB entries
    if "stbs" in data and all(
        k not in data or isinstance(data[k], dict) and k not in ("stbs",)
        for k in incoming
    ):
        # treat incoming as STB entries
        data.setdefault("stbs", {})
        _deep_merge(data["stbs"], incoming)
    else:
        # general deep-merge at top-level
        _deep_merge(data, incoming)

    # write it back
    with open(config_file, 'w') as f:
        json.dump(data, f, indent=4)

    return jsonify({"success": True, "merged": incoming}), 200

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


@app.route('/dart/<stb_name>/<button_id>/<action>/', methods=['GET', 'POST'], strict_slashes=False)
def handle_dart(stb_name, button_id, action):
    # Call the instance method from the Flask app
    response = app.config['controller'].dart(stb_name, button_id, action)
    return response


@app.route('/auto/<remote>/<stb_name>/<button_id>/<delay>/', methods=['GET', 'POST'], strict_slashes=False)
@app.route('/auto/<remote>/<stb_name>/<button_id>/<delay>', methods=['GET', 'POST'], strict_slashes=False)
def handle_auto_remote(remote, stb_name, button_id, delay):
    global press_count  # Use the global counter
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
            press_count += 1  # Increment press count
            response = app.config['controller'].rf_remote(com_port, remote, button_id, delay)
            # time.sleep(delay)
            # response = app.config['controller'].rf_remote(com_port, remote, 'allup', delay)

            # Call 'reset' every 10 presses
            # if press_count % 10 == 0:
            # response = app.config['controller'].rf_remote(com_port, remote, 'reset', delay)
            # logging.info(f"Reset command sent after {press_count} button presses.")

        elif protocol == 'SGS':
            response = app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, button_id, delay)

        return jsonify({'BOOM': response, 'timestamp': datetime.now(timezone.utc).isoformat()})

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
        # print("Discovered IPs:", stb_ip)

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


@app.route('/triggered/<date>/<machine_name>/<stb_name>/<category_id>/<event_id>', methods=['GET', 'POST'],
           strict_slashes=False)
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

        # print(f"stb_ip {stb_ip} protocol {protocol} ")
        if protocol == 'RF':
            # print("RF")
            app.config['controller'].rf_remote(com_port, remote, 'info', delay)
            app.config['controller'].rf_remote(com_port, remote, 'input', delay)
            app.config['controller'].rf_remote(com_port, remote, 'back', delay)
        if protocol == 'SGS':
            # print("SGS")
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'info', delay)
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'input', delay)
            app.config['controller'].sgs_remote(stb_name, stb_ip, rxid, 'back', delay)

        # Load linked logs
        linked_logs_file = 'linkedlogs.txt'  # Update with the correct path if needed
        with open(linked_logs_file, 'r') as logs_file:
            linked_logs = json.load(logs_file)

        # Find file IDs with the matching event_id
        file_ids = [log['id'] for log in linked_logs if log.get('event_id') == event_id]
        file_id_str = ','.join(map(str, file_ids))
        print(event_id)

        if not file_ids:
            return jsonify({'error': 'No matching logs found for event_id'}), 404

        upload(stb_name, file_id_str, ccshare)  # Use the correct upload destination
        # app.config['controller'].mark_logs(stb_name)
        print(stb_name)

        return jsonify({'status': 'Upload triggered', 'file_ids': file_ids}), 200

    except FileNotFoundError:
        return jsonify({'error': 'Configuration file not found'}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to decode the configuration file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def retry_with_linux_pcs(offending_method, *args, **kwargs):
    """
    Retry the offending method with different 'linux_pc' values from the config file until success.
    """
    try:
        # Load unique linux_pc values from config file
        with open(config_file, 'r') as file:
            config_data = json.load(file)
            linux_pcs = list({stb_info['linux_pc'] for stb_info in config_data['stbs'].values()})
            logging.debug(f"Found unique Linux PCs: {linux_pcs}")

        # Try each linux_pc in the list until one succeeds
        for linux_pc in linux_pcs:
            logging.info(f"Attempting to rerun {offending_method.__name__} with Linux PC: {linux_pc}")
            try:
                # Update kwargs with the new linux_pc value
                kwargs['linux_pc'] = linux_pc
                # Retry the offending method with the current linux_pc
                return offending_method(*args, **kwargs)
            except Exception as retry_error:
                logging.error(f"Failed with Linux PC {linux_pc}: {retry_error}")
                continue

        # If none of the Linux PCs work, raise an error
        logging.error(f"All Linux PCs failed for {offending_method.__name__}.")
        raise RuntimeError(f"All Linux PCs failed for {offending_method.__name__}")

    except Exception as e:
        logging.error(f"Error in retry_with_linux_pcs: {str(e)}")
        raise


@app.route('/54/<remote>/<button_id>', methods=['GET', 'POST'], strict_slashes=False)
def handle_54_remote_defaultdelay(com_port, remote, button_id):
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


@app.route('/cc_share_software', methods=['GET', 'POST'], strict_slashes=False)
def get_ccshare_software_and_apps(linux_pc=None):
    """Populates software.txt with files ending in .update and apps_list.txt with files ending in .tgz"""

    if linux_pc is None:
        # Start by using the default Linux PC from credentials
        credentials = load_credentials()
        linux_pc = credentials['linux_pc']

    software_list_file = os.path.join(os.getcwd(), 'software.txt')  # Path to software list file
    apps_list_file = os.path.join(os.getcwd(), 'apps_list.txt')  # Path to apps list file
    software_list = []
    apps_list = []
    remote_base_path = '/ccshare/linux/c_files/'  # Base path to search for software
    remote_apps_path = '/ccshare/linux/c_files/signed-browser-applications/internal/'  # Base path to search for apps

    try:
        logging.debug("Starting get_ccshare_software_and_apps process.")

        # Get credentials
        credentials = load_credentials()
        username = credentials['username']
        password = credentials['password']

        logging.debug(f"Connecting to Linux PC at {linux_pc} with user {username}")

        # Connect via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)

        # Open SFTP connection
        sftp = ssh.open_sftp()
        logging.debug(f"Connected to SFTP on {linux_pc}")

        # Get Apps List (.tgz files)
        logging.debug(f"Listing files in {remote_apps_path}")
        try:
            file_list = sftp.listdir_attr(remote_apps_path)
            sorted_files = sorted(file_list, key=lambda x: x.st_mtime, reverse=True)

            for file in sorted_files:
                if file.filename.endswith('tgz'):
                    file_date = datetime.fromtimestamp(file.st_mtime).strftime('%Y-%m-%d')
                    file_entry = {"filename": file.filename, "date": file_date}
                    apps_list.append(file_entry)
                    logging.debug(f"Added app: {file_entry}")

            # Write apps list to apps_list.txt
            with open(apps_list_file, 'w') as json_file:
                json.dump(apps_list, json_file, indent=4)
            logging.info(f"Apps list saved to {apps_list_file}")
        except FileNotFoundError as fnf_error:
            logging.error(f"Directory {remote_apps_path} not found: {fnf_error}")

        # Get Software List (.update files)
        logging.debug(f"Listing directories in {remote_base_path}")
        remote_dirs = [dir for dir in sftp.listdir(remote_base_path) if dir.endswith('Update')]
        logging.debug(f"Found Update directories: {remote_dirs}")

        # Get all directories in the 'builds_release' folder
        builds_release_path = os.path.join(remote_base_path, 'builds_release')
        logging.debug(f"Listing directories in {builds_release_path}")

        builds_release_dirs = sftp.listdir(builds_release_path)
        logging.debug(f"Found builds_release directories: {builds_release_dirs}")

        # Add the correct paths for builds_release directories
        remote_dirs.extend([f'builds_release/{dir}' for dir in builds_release_dirs])
        logging.debug(f"Total directories to process: {remote_dirs}")

        # Iterate over each Update directory
        for update_dir in remote_dirs:
            update_path = os.path.join(remote_base_path, update_dir)
            logging.debug(f"Listing files in {update_path}")

            try:
                file_list = sftp.listdir_attr(update_path)
            except FileNotFoundError as fnf_error:
                logging.error(f"Directory {update_path} not found: {fnf_error}")
                continue

            sorted_files = sorted(file_list, key=lambda x: x.st_mtime, reverse=True)

            # Filter and add .update files
            for file in sorted_files:
                if file.filename.endswith('.update'):
                    file_date = datetime.fromtimestamp(file.st_mtime).strftime('%Y-%m-%d')
                    file_entry = {"update_dir": update_dir, "filename": file.filename, "date": file_date}
                    software_list.append(file_entry)
                    logging.debug(f"Added software: {file_entry}")

        # Write software list to software.txt
        logging.debug(f"Writing software list to {software_list_file}")
        with open(software_list_file, 'w') as json_file:
            json.dump(software_list, json_file, indent=4)
        logging.info(f"Software list saved to {software_list_file}")

        # Close connections
        sftp.close()
        ssh.close()

        logging.debug("SFTP and SSH connections closed.")
        logging.info(f"Software and apps lists updated successfully.")

        return jsonify({"status": "Software and Apps lists updated successfully"}), 200

    except (paramiko.SSHException, paramiko.ssh_exception.NoValidConnectionsError) as ssh_error:
        logging.error(f"SSH Error: {ssh_error}")
        # Use the retry method to attempt other Linux PCs
        return retry_with_linux_pcs(get_ccshare_software_and_apps)

    except Exception as e:
        logging.error(f"Error in get_ccshare_software_and_apps: {str(e)}")
        return jsonify({"error": f"Failed to update software and apps lists: {str(e)}"}), 500


@app.route('/api/apps', methods=['GET'])
def get_apps_list():
    try:
        with open(apps_list_file, 'r') as json_file:
            apps_list = json.load(json_file)
        return jsonify(apps_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get-software-list', methods=['GET'])
def populate_software_list():
    """Returns the software list from the software.txt file."""
    software_list_file = os.path.join(os.getcwd(), 'software.txt')
    logging.debug(f"Reading software list from {software_list_file}")

    try:
        with open(software_list_file, 'r') as file:
            software_list = json.load(file)
        return jsonify(software_list)
    except Exception as e:
        logging.error(f"Error reading software list: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-local-software', methods=['POST'])
def upload_local_software():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        selected_stb = request.form.get('stb')
        file_type = request.form.get('file_type')

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Save the file to local_apps directory
        apps_dir = f'/home/{username}/stbmnt/apps'
        local_apps = os.path.join(apps_dir, file.filename)
        file.save(local_apps)

        # Load credentials
        credentials = load_credentials()
        linux_pc = credentials.get('linux_pc')
        username = credentials.get('username')
        password = credentials.get('password')
        logging.debug(f"Loaded credentials for user: {username}")

        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        sftp = ssh.open_sftp()
        logging.info(f"Connected to Linux PC: {linux_pc}")

        linux_pc_dir = f'/home/{username}/stbmnt/apps'
        linux_pc_app = os.path.join(linux_pc_dir, file.filename).replace("\\", "/")

        # Ensure the Linux PC directory exists
        try:
            sftp.chdir(linux_pc_dir)
        except IOError:
            logging.info(f"Creating directory on Linux PC: {linux_pc_dir}")
            ssh.exec_command(f"mkdir -p {linux_pc_dir}")

        # Upload the software to the Linux PC if it does not already exist there
        try:
            sftp.stat(linux_pc_app)
            logging.info(f"Software already exists on Linux PC: {linux_pc_app}")
        except FileNotFoundError:
            logging.info(f"Uploading {file.filename} to {linux_pc_app}.")
            sftp.put(local_apps, linux_pc_app)

        # Set appropriate permissions after upload
        ssh.exec_command(f"chmod 755 {linux_pc_app}")

        sftp.close()
        ssh.close()
        logging.info(f"Software {file.filename} loaded successfully onto {linux_pc}.")

        data = {
            'stb': selected_stb,
            'software': file.filename,
            'file_type': file_type
        }

        # Call jam_software_internal() after saving the file
        response, status_code = jam_software_internal(data)

        return jsonify(response), status_code

    except Exception as e:
        logging.error(f"Error during {file_type} upload: {str(e)}")
        return jsonify({'error': str(e)}), 500


def jam_software_internal(data):
    try:
        selected_file = data.get('software')
        selected_stb = data.get('stb')
        file_type = data.get('file_type')

        if not selected_file or not selected_stb:
            return {'error': 'Software or STB not selected'}, 400

        # Refactored logic to handle software JAMming after upload
        apps_dir = f'/home/{username}/stbmnt/apps'
        local_apps = os.path.join(apps_dir, selected_file)

        with open(config_file, 'r') as file:
            config_data = json.load(file)
            stbs = config_data.get('stbs', {})
            stb_info = stbs.get(selected_stb)
            if not stb_info:
                logging.error(f"STB {selected_stb} not found in configuration.")
                return {'error': f"STB {selected_stb} not found in configuration"}, 404

            stb_ip = stb_info.get('ip')
            linux_pc = stb_info.get('linux_pc')
            logging.debug(f"STB IP: {stb_ip}, Linux PC: {linux_pc}")

            if not stb_ip:
                logging.error(f"Failed to find IP for STB: {selected_stb}")
                return {'error': f"Failed to find IP for STB: {selected_stb}"}, 404

        logging.info(f"Preparing to JAM {file_type} {selected_file} onto STB {selected_stb}")

        credentials = load_credentials()
        username = credentials.get('username')
        password = credentials.get('password')
        logging.debug(f"Loaded credentials for user: {username}")

        if file_type == "software":
            run_commands_over_ssh(linux_pc, username, password, stb_ip, selected_file)
        elif file_type == "app":
            # Form the data and call load_app() with the correct form data
            form_data = {
                'stb': selected_stb,
                'app': selected_file
            }
            load_app_internal(form_data)

        return {'status': f"{file_type.capitalize()} successfully JAMmed"}, 200

    except Exception as e:
        logging.error(f"Error during {file_type} JAMming: {str(e)}")
        return {'error': str(e)}, 500


def load_app_internal(data):
    with app.test_request_context('/api/load_app', method='POST', data=data):
        return load_app()


def record_jam_event(selected_stb, selected_file, jam_events_file='jam_events.json'):
    """
    Record a jam event for a given STB.

    Instead of appending a new record for every event,
    this function updates the event for a given STB, overwriting the
    'file' and 'jam_time'. If the STB does not already exist in the file,
    it is added.

    :param selected_stb: The STB identifier (string)
    :param selected_file: The software file name (string)
    :param jam_events_file: The filename for storing jam events (default 'jam_events.json')
    """
    try:
        # If the jam_events file exists, load its contents; otherwise, use an empty dict.
        if os.path.exists(jam_events_file):
            with open(jam_events_file, 'r') as f:
                try:
                    events = json.load(f)
                except Exception as e:
                    logging.error("Error parsing JSON from jam_events.json: " + str(e))
                    events = {}
        else:
            events = {}

        # Overwrite or add the entry for this STB.
        events[selected_stb] = {
            "file": selected_file,
            "jam_time": datetime.now().isoformat()
        }

        # Write updated events back to the file.
        with open(jam_events_file, 'w') as f:
            json.dump(events, f, indent=2)

        logging.info(f"Recorded jam event for STB {selected_stb}: file {selected_file}, jam_time updated.")
    except Exception as e:
        logging.error(f"Error updating jam_events.json for {selected_stb}: {e}")

@app.route('/jam-software', methods=['GET', 'POST'], strict_slashes=False)
def jam_software(stb_name=None, software=None):
    logging.debug("Received request to load software.")

    # Check if it's a GET request with URL parameters or POST request with JSON
    if stb_name and software:
        selected_stb = stb_name
        selected_file = software
        # For GET, you might not have a "directory" parameter, so set it appropriately.
        selected_dir = "default_update_dir"
    else:
        data = request.json
        selected_dir = data.get('directory')  # The parent directory (update_dir)
        selected_file = data.get('software')  # The software file (filename)
        selected_stb = data.get('stb')

    logging.debug(
        f"Selected software: {selected_file}, Selected Directory: {selected_dir}, Selected STB: {selected_stb}"
    )

    if not selected_file or not selected_stb or not selected_dir:
        logging.error("Software, directory, or STB not selected.")
        return jsonify({'error': 'Software, directory, or STB not selected'}), 400

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
        # If linux_pc comes from the config, you might not need to override it.
        linux_pc = credentials.get('linux_pc', linux_pc)
        logging.debug(f"Loaded credentials for user: {username}")

        # Establish SSH connection to Linux PC
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        sftp = ssh.open_sftp()
        logging.info(f"Connected to Linux PC: {linux_pc}")

        # Construct the CC Share path using the update_dir and the software filename
        cc_share = f"/ccshare/linux/c_files/{selected_dir}/{selected_file}"
        apps_dir = f'/home/{username}/stbmnt/apps'
        local_apps = os.path.join(apps_dir, selected_file)
        linux_pc_dir = f'/home/{username}/stbmnt/apps'
        linux_pc_app = os.path.join(linux_pc_dir, selected_file).replace("\\", "/")

        logging.debug(
            f"Software filename: {selected_file}, CC Share Path: {cc_share}, "
            f"Local Apps Path: {local_apps}, Linux PC App Path: {linux_pc_app}"
        )

        # Ensure the local apps directory exists
        if not os.path.exists(apps_dir):
            os.makedirs(apps_dir)
            logging.info(f"Created local apps directory: {apps_dir}")

        # Download the software if not already available locally
        if not os.path.exists(local_apps):
            logging.info(f"Downloading {selected_file} from CC Share.")
            sftp.get(cc_share, local_apps)
        else:
            logging.info(f"{selected_file} already exists locally, skipping download.")

        # Ensure the Linux PC directory exists
        try:
            sftp.chdir(linux_pc_dir)
            logging.info(f"Changed to Linux PC directory: {linux_pc_dir}")
            ssh.exec_command(f"ls -l")
        except IOError:
            logging.info(f"Creating directory on Linux PC: {linux_pc_dir}")
            ssh.exec_command(f"mkdir -p {linux_pc_dir}")

        # Upload the software to the Linux PC if it does not already exist there
        try:
            sftp.stat(linux_pc_app)
            logging.info(f"Software already exists on Linux PC: {linux_pc_app}")
            ssh.exec_command(f"chmod 755 {linux_pc_app}\r")
            ssh.exec_command(f"ls -l {linux_pc_app}\r")
            logging.info(f"chmod'ing {linux_pc_app}.")
        except FileNotFoundError:
            logging.info(f"Uploading {local_apps} to {linux_pc_app}.")
            sftp.put(local_apps, linux_pc_app)
            ssh.exec_command(f"chmod 755 {linux_pc_app}\r")
            logging.info(f"chmod'ing {linux_pc_app}.")
            ssh.exec_command(f"ls -l {linux_pc_app}\r")

        sftp.close()
        ssh.close()
        logging.info(f"Software {selected_file} loaded successfully onto {linux_pc}.")

        # Record the jam event in our JSON log.
        record_jam_event(selected_stb, selected_file)

        result = run_commands_over_ssh(linux_pc, username, password, stb_ip, selected_file)

        # Now 'result' is a dict, e.g. {'status': 'update complete'} or
        # {'status': 'no update complete detected'} or an error string
        if result.get('status', '').lower() == 'update complete':
            return jsonify({'status': 'Update Complete! Software successfully JAMmed!'}), 200
        elif result.get('status', '').startswith('error:'):
            return jsonify({'error': result['status']}), 500
        else:
            return jsonify({'status': 'Software loaded, but no update complete detected'}), 200

    except Exception as e:
        logging.error(f"Error during software load: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Set up logging to file
logging.basicConfig(
    filename='logJAM.txt',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

log_output = ""  # Global variable to hold the tnet.jam output


@app.route('/api/load_app', methods=['POST'])
@app.route('/api/load_app/<stb_name>/<app>', methods=['GET'])
def load_app(stb_name=None, app=None):
    logging.debug("Received request to load app.")

    # Check if it's a GET request with URL parameters or POST request with JSON/form-data
    if request.method == 'GET' and stb_name and app:
        selected_stb = stb_name
        selected_file = app
    else:
        if request.is_json:  # Handle JSON request (external API call)
            data = request.json
            selected_file = data.get('app')
            selected_stb = data.get('stb')
        else:  # Handle form-data (internal API call)
            selected_file = request.form.get('app')
            selected_stb = request.form.get('stb')

    logging.debug(f"Selected app: {selected_file}, Selected STB: {selected_stb}")

    if not selected_file or not selected_stb:
        logging.error("App or STB not selected.")
        return jsonify({'error': 'App or STB not selected'}), 400

    local_apps = os.path.join(apps_dir, selected_file)

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
        linux_pc = credentials.get('linux_pc')
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
            logging.warning(
                f"Unexpected file format for selected_file: {selected_file}. Using full string as app filename.")

        cc_share = f"/ccshare/linux/c_files/signed-browser-applications/internal/{app_filename}"
        apps_dir = f'/home/{username}/stbmnt/apps'
        local_apps = os.path.join(apps_dir, app_filename)
        linux_pc_dir = f'/home/{username}/stbmnt/apps'
        linux_pc_app = os.path.join(linux_pc_dir, selected_file).replace("\\", "/")

        logging.debug(
            f"App filename: {app_filename},\n CC Share Path: {cc_share},\n Local Apps Path: {local_apps},\n Linux PC App Path: {linux_pc_app}")

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

        run_commands_over_ssh(linux_pc, username, password, stb_ip, app)
        return jsonify({'status': 'App successfully prepared'}), 200
    except Exception as e:
        logging.error(f"Error during app load: {str(e)}")
        return jsonify({'error': str(e)}), 500


def run_commands_over_ssh(linux_pc, username, password, stb_ip, app):
    """
    Runs an 'expect' command over SSH and reads stdout line by line until it
    detects "Update Complete" or the command finishes. Returns a dict:
      {'status': 'update complete'} if found,
      {'status': 'no update complete detected'} otherwise.
    """

    logging.debug("Starting run_commands_over_ssh function.")
    logging.debug(f"Parameters received - Linux PC: {linux_pc}, Username: {username}, STB IP: {stb_ip}, App: {app}")

    ssh = None
    try:
        logging.info(f"Attempting to SSH into {linux_pc}.")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        logging.info(f"SSH connection established with {linux_pc}.")

        # Paths
        linux_pc_stbmnt = f'/home/{username}/stbmnt'
        tnet_remote_path = f"{linux_pc_stbmnt}/tnet.jam"
        tnet_local = 'tnet.jam'
        logging.debug(f"Remote tnet.jam path: {tnet_remote_path}, Local tnet.jam path: {tnet_local}")

        # 1. SFTP upload
        sftp = ssh.open_sftp()
        try:
            logging.info(f"Uploading tnet.jam to {linux_pc}:{tnet_remote_path}.")
            sftp.put(tnet_local, tnet_remote_path)
            logging.debug(f"tnet.jam uploaded successfully to {tnet_remote_path}.")
            print(f"tnet.jam uploaded successfully to {tnet_remote_path}.")
        except FileNotFoundError:
            logging.error(f"tnet.jam not found locally or unable to upload to {tnet_remote_path}.")
            raise
        sftp.close()

        # 2. Construct and run the command
        command = f"expect {tnet_remote_path} {stb_ip} apps {app}"
        logging.info(f"Running command on {linux_pc}: {command}")

        # Possibly use get_pty=True for interactive commands
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

        found_update_complete = False

        # read line by line until command finishes or we see 'Update Complete'
        while not stdout.channel.exit_status_ready():
            line = stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            line_stripped = line.strip()
            logging.info(f"[STDOUT] {line_stripped}")

            # Check for 'Update Complete'
            if re.search(r'update complete', line_stripped, re.IGNORECASE):
                logging.info("Detected 'Update Complete' in the command output.")
                found_update_complete = True
                return {'status': 'Update Complete'}

            # Check for 'boot recovery'
            if re.search(r'please put your box in boot recovery', line_stripped, re.IGNORECASE):
                logging.info("Detected 'please put your box in boot recovery'. Initiating boot recovery...")
                boot_recovery(linux_pc, username, password, stb_ip, tnet_remote_path)
                logging.info("Sleeping 60 seconds then re-running run_commands_over_ssh...")
                time.sleep(90)
                # Re-run after recovery
                ssh.close()
                return run_commands_over_ssh(linux_pc, username, password, stb_ip, app)

        # Drain remaining output
        remaining = stdout.read().decode(errors='ignore').strip()
        if remaining:
            logging.info(f"[STDOUT-REMAINING] {remaining}")
            if re.search(r'update complete', remaining, re.IGNORECASE):
                found_update_complete = True

        # Check stderr
        err_output = stderr.read().decode(errors='ignore').strip()
        if err_output:
            logging.error(f"[STDERR] {err_output}")

        if found_update_complete:
            logging.info("Update Complete recognized. Returning success.")
            return {'status': 'Update Complete'}

        logging.info("SSH command execution complete (no 'Update Complete' found).")
        return {'status': 'no update complete detected'}

    except Exception as e:
        logging.error(f"Failed to execute commands over SSH: {e}")
        return {'status': f'error: {e}'}

    finally:
        if ssh:
            ssh.close()
            logging.info("SSH connection closed.")
        logging.info("Stopping any music playback (pygame).")
        pygame.mixer.music.stop()  # remove if not needed


# Endpoint to retrieve the log output for the webpage
@app.route('/get_log_output', methods=['GET'])
def get_log_output():
    global log_output
    return jsonify({'log_output': log_output})


def boot_recovery(linux_pc, username, password, stb_ip, tnet_remote_path):
    logging.debug("Starting boot_recovery function.")
    try:
        logging.info(f"Attempting to SSH into {linux_pc} for boot recovery.")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(linux_pc, username=username, password=password)
        logging.info(f"SSH connection established with {linux_pc} for boot recovery.")

        # Corrupt VNVM to force boot recovery
        corrupt_command = f"dd if=/dev/mtd1 of=/tmp/mtd1_start bs=1 count=$((0x1FB48)) && dd if=/dev/zero of=/tmp/zero bs=1 count=$((0x184)) && dd if=/dev/mtd1 of=/tmp/mtd1_end bs=1 skip=$((0x1FB48+0x184)) && cat /tmp/mtd1_start /tmp/zero /tmp/mtd1_end > /tmp/mtd1_new && flash_unlock -u /dev/mtd1 && flashcp -v /tmp/mtd1_new /dev/mtd1"
        reboot_command = "reboot"
        tnet_command = f"expect {tnet_remote_path} {stb_ip} boot_recovery"

        logging.info(f"Running VNVM corrupt command on {stb_ip}: {tnet_command}")
        stdin, stdout, stderr = ssh.exec_command(tnet_command)
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            logging.info(f"Output from VNVM corrupt command:\n{output}")
        if error:
            logging.error(f"Error from VNVM corrupt command:\n{error}")
            raise Exception("Error corrupting VNVM")

        # Reboot the box to enter boot recovery
        logging.info(f"Rebooting the set-top box {stb_ip} to enter boot recovery.")
        ssh.exec_command(reboot_command)
        ssh.close()
        logging.info("Boot recovery initiated and SSH connection closed.")

    except Exception as e:
        logging.error(f"Failed to initiate boot recovery: {e}")


# 1) Find the directory containing this file
BASE_DIR = Path(__file__).resolve().parent

# 2) Define the relative filenames you want to track
RELATIVE_FILES = [
    "commands.py",
    "get_stb_list.py",
    "JAMboree.py",
    os.path.join("templates", "JAMboRemote.html"),
    os.path.join("templates", "dayJAM.html"),
]

# 3) Convert them to absolute paths
FILES_TO_TRACK = [str(BASE_DIR / f) for f in RELATIVE_FILES]


def get_db_connection():
    import json
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent
    cred_file = base_dir / "credentials.txt"

    if not cred_file.exists():
        raise FileNotFoundError(f"Could not find 'credentials.txt' in {base_dir}.")
    with open(cred_file, "r") as f:
        creds = json.load(f)

    required = ["db_host", "db_name", "db_username", "db_password"]
    for key in required:
        if key not in creds:
            raise KeyError(f"Missing '{key}' in credentials.txt.")

    conn = psycopg2.connect(
        dbname=creds["db_name"],
        user=creds["db_username"],
        password=creds["db_password"],
        host=creds["db_host"]
    )
    return conn


def calculate_md5(file_path):
    """Calculate MD5 of a file in binary mode."""
    import hashlib
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = r"C:\Users\jacob.montgomery\Documents\JAMboree"
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "versionControl.py")
VERSION_CONTROL_SCRIPT = os.path.join(BASE_DIR, "versionControl.py")


def run_version_control():
    """
    Executes versionControl.py, parses the output, and returns JSON-friendly data.

    Expected script output lines look like:
      - v.4 : 5   ⚠️ Some file name here
    or
      - v.4 : 4   Up to date  Some file name here

    Adjust the parsing if your actual format differs.
    """
    if not os.path.exists(VERSION_CONTROL_SCRIPT):
        return {
            "success": False,
            "error": f"File not found: {VERSION_CONTROL_SCRIPT}",
        }

    try:
        # Use sys.executable so we call the same Python environment
        result = subprocess.run(
            [sys.executable, VERSION_CONTROL_SCRIPT],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(VERSION_CONTROL_SCRIPT),  # Run in that dir
            encoding="utf-8",
            errors="replace",  # replace invalid chars
            check=False  # don't raise CalledProcessError automatically
        )

        # Check return code
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Script exited with code {result.returncode}",
                "stderr": result.stderr,
                "raw_output": result.stdout,
            }

        # Parse lines
        version_data = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("- v."):  # example: "- v.4 : 5   ⚠️ SomeFile..."
                # Example line: "- v.4 : 5   ⚠️ Using older version   commands.py"
                # We'll parse in 2 steps:
                # 1) parts[0] = '- v.4 : 5'
                # 2) The rest might have '⚠️ Using older version' or 'Up to date' or ...
                # 3) Then the file name.
                # Let's do a quick split approach:

                # Split at two spaces or some delimiter (this is flexible if your real lines differ)
                # We'll do simpler: let's separate left side from right side on two spaces
                splitted = line.split("  ", 1)  # first part (version info), second part (status + file)
                left_side = splitted[0].replace("- v.", "").strip()  # e.g. "4 : 5"
                right_side = splitted[1].strip() if len(splitted) > 1 else ""

                # left_side might be "4 : 5"
                # we'll parse in_use_version = 4, latest_version = 5
                in_use, latest = left_side.split(":", 1)
                in_use_version = in_use.strip()
                latest_version = latest.strip()

                # For the right_side, we guess if it has a status or not
                # e.g. "⚠️ Using older version   commands.py" or "Up to date   commands.py"
                # We'll do a second .split on double spaces, or just find last chunk as file
                status_part = ""
                file_part = ""
                # We'll do a final approach: the last word is the file name (or more).
                # That might not be robust if the file name can have spaces, but let's see:
                # If the file name can have spaces, we might need a more advanced parse.
                # We'll assume the file name is everything after the last group of spaces.

                # Attempt:
                right_tokens = right_side.rsplit(" ", 1)
                if len(right_tokens) == 2:
                    # last chunk is the file, first chunk is the status
                    status_part = right_tokens[0].strip()
                    file_part = right_tokens[1].strip()
                else:
                    # fallback
                    file_part = right_side

                # Distinguish if status_part has "Up to date" or "⚠️ Using older version"
                # If it doesn't have those, we can guess "New version" or something
                if "Up to date" in status_part:
                    status = "Up to date"
                elif "⚠️" in status_part or "older" in status_part:
                    status = "⚠️ Using older version"
                else:
                    status = "Unknown or new"

                version_data.append({
                    "file": file_part,
                    "version_in_use": in_use_version,
                    "latest_version": latest_version,
                    "status": status
                })

        if not version_data:
            return {
                "success": False,
                "error": "No version data parsed from script output.",
                "raw_output": result.stdout
            }

        return {"success": True, "version_data": version_data}

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to run version control script: {e}",
        }


@app.route("/api/version-control", methods=["GET"])
def api_version_control():
    """
    Flask endpoint that returns the version control data in JSON.
    """
    data = run_version_control()
    if not data["success"]:
        return jsonify({
            "success": False,
            "error": data.get("error", "Unknown error"),
            "raw_output": data.get("raw_output", ""),
        }), 500

    return jsonify({
        "success": True,
        "version_data": data["version_data"]
    })


fetcher = JAMboree_gui()
if __name__ == '__main__':
    # app = JAMboree_gui()
    # app.mainloop()
    app.config['controller'] = fetcher
    # app.config['controller'] = JAMboree_gui()
    app.config['controller'].mainloop()
