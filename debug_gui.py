import json
import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import sys
from flask import Flask, jsonify, request
import paramiko
import threading
import stat
import gzip
import shutil
import socket
import time
from tkinterdnd2 import TkinterDnD, DND_FILES
import pygame
from translate_script import translate_file
from dayJAM import SetTopJAM


pygame.mixer.init()

app = Flask(__name__)

HOST = "https://grasshopper-autoupload.dishanywhere.com:8443"
PORT = "8443"
GNAT_AUTH_KEY = "OvXzQivJdXxJdXWmGY6sckp0MX3zeWpv"
upload_path = 'grasshopper-smp/rest/v2/request/upload'
partial_upload_path = 'grasshopper-smp/rest/v2/request/partial-upload'
uploadable_files_path = 'grasshopper-smp/rest/v1/stb-uploadable-files'
uploadable_file_groups_path = 'grasshopper-smp/rest/v1/stb-uploadable-file-groups'
user = socket.gethostname()

s3 = 'https://ds-ghuh.dishtv.technology/upload'
ccshare = 'https://stbAnalyticsDU.echostarbeta.com/cgi-bin/ghuh'

upload_destination = ccshare

file_id = '20'

script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary
sys.path.append(script_dir)

config_file = 'base.txt'
found_stbs_file = 'found_stbs.json'
credentials_file = 'credentials.json'

def save_credentials(username, password):
    credentials = {'username': username, 'password': password}
    with open(credentials_file, 'w') as file:
        json.dump(credentials, file)

def load_credentials():
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as file:
            return json.load(file)
    return {'username': '', 'password': ''}
    

def run_curl_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

def upload(stb_name, file_id, upload_destination):
    try:
        upload_results = []
        if os.path.exists('upload_results.json'):
            with open('upload_results.json', 'r') as json_file:
                upload_results = json.load(json_file)

        with open(config_file, 'r') as file:
            config_data = json.load(file)

        stb_details = config_data['stbs'].get(stb_name)
        if not stb_details:
            print(f'STB {stb_name} not found')
            return

        receiver_id = stb_details.get('stb')[:11]
        curl_command = (f'curl --location "{HOST}/{upload_path}" '
                        f'--header "Content-Type: application/json" '
                        f'--header "Gnat-Authorization-Key: {GNAT_AUTH_KEY}" '
                        f'--data "{{\\"user\\": \\"{user}\\", \\"receiver_ids\\": [\\"{receiver_id}\\"], \\"upload_destination\\": \\"{upload_destination}\\", \\"file_ids\\": [{file_id}]}}"')
        stdout, stderr = run_curl_command(curl_command)
        if stdout:
            try:
                response_data = json.loads(stdout)
                request_id = response_data
                upload_results.append({
                    'receiver_id': receiver_id,
                    'request_id': request_id,
                    'file_id': file_id
                })
                print(f"Request for {receiver_id}: {request_id} and File ID: {file_id} to {upload_destination}")
            except json.JSONDecodeError:
                print("Failed to decode JSON response.")
        
        # Save results to JSON file
        with open('upload_results.json', 'w') as json_file:
            json.dump(upload_results, json_file, indent=4)

    except Exception as e:
        print(f"Failed to upload file {file_id} for STB {stb_name}: {e}")
        
def update_stb_ip():
    with open(config_file, 'r') as file:
        config_data = json.load(file)
    with open(found_stbs_file, 'r') as file:
        found_stbs = json.load(file)

    updated = False

    for new_stb, details in found_stbs.items():
        new_ip = details['ip'].split(':')[0]  # Strip the port from the IP address
        model = details.get('model_name') or details.get('model')
        stb = details.get('stb')

        found = False
        for device_name, device_info in config_data['stbs'].items():
            if device_info['stb'] == stb:
                found = True
                if device_info['ip'] != new_ip:
                    config_data['stbs'][device_name]['ip'] = new_ip
                    updated = True
                    print(f"Updated IP for {stb} to {new_ip}")
                else:
                    print(f"No update needed for {stb}, IP remains {new_ip}")
                break
        
        if not found:
            new_name = f"{model}-{len(config_data['stbs']) + 1}"
            config_data["stbs"][new_name] = {
                'stb': stb,
                'ip': new_ip,
                'model': model,
                'sw_ver': "",
                'protocol': 'SGS',
                'remote': '0',
                "lname": "",
                "passwd": "",
                "linux_pc": "",
                "com_port": "",
                "master_stb": "",
                "rid": ""
            }
            updated = True
            print(f"Added {new_name} with IP {new_ip} and STB {stb}.")

    if updated:
        with open(config_file, 'w') as file:
            json.dump(config_data, file, indent=4)


class DebugGUI(tk.Toplevel):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)
        self.title('Debug Menu')
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        # Create the 'Credentials' tab
        self.credentials_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.credentials_frame, text='Credentials')
        self.create_credentials_tab()

        # Create the 'Request' tab
        self.request_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.request_frame, text='Request')
        self.create_request_tab()

        # Create the 'Download' tab
        self.download_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.download_frame, text='Download')
        self.create_download_tab()
        
        # Create the 'Bulk' tab
        self.bulk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bulk_frame, text='Bulk')
        self.create_bulk_tab()


        # Create the 'Key Logs' tab
        self.key_logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.key_logs_frame, text='Key Logs')
        self.create_key_logs_tab()

        try:
            self.selected_stbs = self.get_selected_stbs()
        except Exception as e:
            print("Failed to load selected STBs:", str(e))
            self.selected_stbs = []

        # Start the STB search in the background
        #self.start_stb_search()

        # Create the 'dailyJAM' tab
        self.dailyjam_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dailyjam_frame, text='dailyJAM')
        self.create_dailyjam_tab()

        try:
            self.selected_stbs = self.get_selected_stbs()
        except Exception as e:
            print("Failed to load selected STBs:", str(e))
            self.selected_stbs = []
            
    def create_credentials_tab(self):
        credentials = load_credentials()

        self.username_label = ttk.Label(self.credentials_frame, text="Username")
        self.username_label.grid(row=0, column=0, padx=5, pady=5)
        ToolTip(self.username_label, "Enter your super-secret username here.")

        self.username_entry = ttk.Entry(self.credentials_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        self.username_entry.insert(0, credentials['username'])

        self.password_label = ttk.Label(self.credentials_frame, text="Password")
        self.password_label.grid(row=1, column=0, padx=5, pady=5)
        ToolTip(self.password_label, "Shh, it's a secret! Type your password here.")

        self.password_entry = ttk.Entry(self.credentials_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        self.password_entry.insert(0, credentials['password'])

        self.save_button = ttk.Button(self.credentials_frame, text="Save", command=self.save_credentials)
        self.save_button.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(self.save_button, "Click here to save your top-secret credentials.")

    def save_credentials(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        save_credentials(username, password)
        print("Credentials saved.")

    def create_request_tab(self):
        self.upload_destination_var = tk.StringVar(value='ccshare')

        self.ccshare_label = ttk.Label(self.request_frame, text="ccshare", style='TLabel')
        self.ccshare_label.grid(row=0, column=0, padx=2, pady=2, sticky='e')
        ToolTip(self.ccshare_label, "Upload your settops logs to The mystical CCShare destination.")
        
        self.s3_label = ttk.Label(self.request_frame, text="s3", style='TLabel')
        self.s3_label.grid(row=0, column=2, padx=2, pady=2, sticky='w')
        ToolTip(self.s3_label, "Upload your logs to Amazon's storage kingdom.")

        self.destination_toggle = ttk.Checkbutton(
            self.request_frame, text="Upload Dest", variable=self.upload_destination_var,
            onvalue='s3', offvalue='ccshare', style='TButton', command=self.update_labels
        )
        self.destination_toggle.grid(row=0, column=1, padx=2, pady=2)
        ToolTip(self.destination_toggle, "Toggle between s3 and ccshare for your uploads.")

        self.scrollbar = ttk.Scrollbar(self.request_frame, orient="vertical")
        self.scrollbar.grid(row=1, column=4, rowspan=8, sticky='ns')

        self.listbox = tk.Listbox(self.request_frame, selectmode=tk.MULTIPLE, yscrollcommand=self.scrollbar.set, width=30, height=20)
        self.listbox.grid(row=1, column=3, rowspan=8, padx=5, pady=5)
        ToolTip(self.listbox, "Select the logs you'd like to request.")
        self.scrollbar.config(command=self.listbox.yview)

        self.check_channel_btn = ttk.Button(self.request_frame, text="Whatcha\nWatchin?", command=self.master.check_channel, style='TButton')
        self.check_channel_btn.grid(row=6, column=0, padx=5, pady=5)
        ToolTip(self.check_channel_btn, "Check what your tuners are tuned in to.")
        
        self.check_multicast_btn = ttk.Button(self.request_frame, text="Multicasts", command=self.master.check_multicast, style='TButton')
        self.check_multicast_btn.grid(row=6, column=1, padx=5, pady=5)
        ToolTip(self.check_multicast_btn, "See what muticasts your tuners are subscribing to")

        self.mark_logs_btn = ttk.Button(self.request_frame, text="Mark Logs", command=self.master.mark_logs, style='TButton')
        self.mark_logs_btn.grid(row=1, column=0, padx=5, pady=5)
        ToolTip(self.mark_logs_btn, "Send settop status and mark the logs")
        
        self.get_logs_btn = ttk.Button(self.request_frame, text="Direct Dev dl", command=self.master.call_get_dev_logs, style='TButton')
        self.get_logs_btn.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(self.get_logs_btn, "If the settop is unsecured, this will try to go in and download logs. Don't ask how.")
        
        self.update_stb_ip_btn = ttk.Button(self.request_frame, text="Sync STB datbase", command=update_stb_ip, style='TButton')
        self.update_stb_ip_btn.grid(row=4, column=1, padx=2, pady=2)
        ToolTip(self.update_stb_ip_btn, "Sync the database and make sure everyone’s on the same page.")

        # Text input for file versions
        self.file_versions_entry = ttk.Entry(self.request_frame, foreground="grey")
        self.file_versions_entry.insert(0, "# versions")
        self.file_versions_entry.grid(row=3, column=1, padx=5, pady=5)
        ToolTip(self.file_versions_entry, "How many versions do you want? The more, the merrier! (start with 2)")
        self.file_versions_entry.bind("<FocusIn>", self.clear_placeholder)
        self.file_versions_entry.bind("<FocusOut>", self.add_placeholder)

        # New Buttons
        self.upload_btn = ttk.Button(self.request_frame, text="Request Upload", command=self.request_log_upload, style='TButton')
        self.upload_btn.grid(row=3, column=0, padx=5, pady=5)
        ToolTip(self.upload_btn, "Request those logs like a pro! They will go tS3 or ccshare. If you choose ccshare, you can get them from the Download tab")
        
        self.find_btn = ttk.Button(self.request_frame, text="Find Dev's", command=self.master.find_sgs, style='TButton')
        self.find_btn.grid(row=4, column=0, padx=5, pady=5)
        ToolTip(self.find_btn, "Activly searches the networks for Unsecure settops and saves them for later.")

        #self.uploadable_files_btn = ttk.Button(self.request_frame, text="Get Files", command=self.uploadable_files, style='TButton')
        #self.uploadable_files_btn.grid(row=4, column=0, padx=5, pady=5)

        #self.uploadable_file_groups_btn = ttk.Button(self.request_frame, text="Get Groups", command=self.uploadable_file_groups, style='TButton')
        #self.uploadable_file_groups_btn.grid(row=4, column=1, padx=5, pady=5)

        self.unpair_btn = ttk.Button(self.request_frame, text='Unpair', command=self.master.unpair_function)
        self.unpair_btn.grid(row=5, column=0, padx=5, pady=5)
        ToolTip(self.unpair_btn, "Break up with your paired remotes here.")

        self.close_button = ttk.Button(self.request_frame, text="Close", command=self.on_close)
        self.close_button.grid(row=5, column=1)
        ToolTip(self.close_button, "Close this window and say goodbye.", sound_file="sound.mp3")

        self.load_logs_from_json()
        self.update_labels()  # Initial label update

    def create_download_tab(self):
        self.download_scrollbar = ttk.Scrollbar(self.download_frame, orient="vertical")
        self.download_scrollbar.grid(row=1, column=4, rowspan=8, sticky='ns')

        self.download_listbox = tk.Listbox(self.download_frame, selectmode=tk.MULTIPLE, yscrollcommand=self.download_scrollbar.set, width=30, height=20)
        self.download_listbox.grid(row=1, column=3, rowspan=8, padx=5, pady=5)
        ToolTip(self.download_listbox, "Select which logs you want to download.")
        self.download_scrollbar.config(command=self.download_listbox.yview)

        self.download_logs_btn = ttk.Button(self.download_frame, text="Download Logs", command=self.download_logs, style='TButton')
        self.download_logs_btn.grid(row=2, column=0, padx=5, pady=5)
        ToolTip(self.download_logs_btn, "Download those logs! They're yours for the taking.")


        self.refresh_btn = ttk.Button(self.download_frame, text="Refresh", command=self.populate_download_listbox, style='TButton')
        self.refresh_btn.grid(row=3, column=0, padx=5, pady=5)
        ToolTip(self.refresh_btn, "Refresh the list. Sometimes it needs a little nudge.")
        
        #self.grasshopper_download_btn = ttk.Button(self.download_frame, text="Grasshopper\nDownload", command=self.grasshopper_download, style='TButton')
        #self.refresh_btn.grid(row=4, column=0, padx=5, pady=5)

        #self.populate_download_listbox()

    def create_bulk_tab(self):
        # Add a scrollbar and listbox
        scrollbar = ttk.Scrollbar(self.bulk_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bulk_listbox = tk.Listbox(self.bulk_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
        self.bulk_listbox.pack(fill=tk.BOTH, expand=True)
        ToolTip(self.bulk_listbox, "Select multiple STBs for bulk operations.")
        scrollbar.config(command=self.bulk_listbox.yview)

        # Load STBs from config_file
        self.load_stbs_into_bulk_listbox()

        # Bind event to update config on selection
        self.bulk_listbox.bind('<<ListboxSelect>>', self.on_bulk_select)

    def create_key_logs_tab(self):
        self.key_logs_label = ttk.Label(self.key_logs_frame, text="Select files for translation:")
        self.key_logs_label.pack(pady=5)
        ToolTip(self.key_logs_label, "Choose the files you want to translate into something more meaningful.")

        self.file_listbox = tk.Listbox(self.key_logs_frame, height=10, selectmode=tk.MULTIPLE)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ToolTip(self.file_listbox, "Selected files will appear here. Don't worry, they'll be transformed.")


        self.select_files_button = ttk.Button(self.key_logs_frame, text="Select Files", command=self.select_files)
        self.select_files_button.pack(pady=5)
        ToolTip(self.select_files_button, "Click here to choose files from your machine. Let the magic begin.")


        self.translate_button = ttk.Button(self.key_logs_frame, text="Go", command=self.translate_files)
        self.translate_button.pack(pady=5)
        ToolTip(self.translate_button, "Ready, set, translate! Watch those files transform.")
        
    def create_dailyjam_tab(self):
        # Embed the SetTopJAM in this frame
        SetTopJAM(master=self.dailyjam_frame)

    def select_files(self):
        files = filedialog.askopenfilenames()
        for file in files:
            if file not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, file)

    # Method to handle file translation
    def translate_files(self):
        files = self.file_listbox.get(0, tk.END)
        if not files:
            messagebox.showwarning("No Files", "Please select files to translate.")
            return

        for file in files:
            output_file = translate_file(file)
            if "An error occurred" in output_file:
                messagebox.showerror("Error", output_file)
            else:
                messagebox.showinfo("Success", f"Translated file saved as: {output_file}")


    def load_stbs_into_bulk_listbox(self):
        # Clear the listbox before populating
        self.bulk_listbox.delete(0, tk.END)

        try:
            with open(config_file, 'r') as file:
                config_data = json.load(file)

            for stb_name, stb_details in config_data['stbs'].items():
                self.bulk_listbox.insert(tk.END, stb_name)
                # Automatically select items that are marked as "selected": true
                if stb_details.get('selected'):
                    self.bulk_listbox.select_set(tk.END)

        except Exception as e:
            print(f"Failed to load STBs into bulk listbox: {e}")

    def on_bulk_select(self, event):
        # Get the selected indices
        selected_indices = self.bulk_listbox.curselection()
        selected_stbs = [self.bulk_listbox.get(i) for i in selected_indices]

        try:
            with open(config_file, 'r') as file:
                config_data = json.load(file)

            # Update the "selected" field based on listbox selection
            for stb_name, stb_details in config_data['stbs'].items():
                if stb_name in selected_stbs:
                    config_data['stbs'][stb_name]['selected'] = True
                else:
                    config_data['stbs'][stb_name]['selected'] = False

            # Save the updated configuration back to the file
            with open(config_file, 'w') as file:
                json.dump(config_data, file, indent=4)

        except Exception as e:
            print(f"Failed to update selection in config file: {e}")

    def clear_placeholder(self, event):
        if self.file_versions_entry.get() == "# versions":
            self.file_versions_entry.delete(0, tk.END)
            self.file_versions_entry.config(foreground="black")

    def add_placeholder(self, event):
        if not self.file_versions_entry.get():
            self.file_versions_entry.insert(0, "# versions")
            self.file_versions_entry.config(foreground="grey")

    def update_labels(self):
        if self.upload_destination_var.get() == 'ccshare':
            self.ccshare_label.config(foreground='green')
            self.s3_label.config(foreground='red')
        else:
            self.ccshare_label.config(foreground='red')
            self.s3_label.config(foreground='green')

    def on_close(self):
        self.destroy()

    def get_selected_stbs(self):
        os.chdir(script_dir)
        with open(config_file) as file:
            config = json.load(file)
        stbs_dict = config.get('stbs', {})
        if not isinstance(stbs_dict, dict):
            raise ValueError("STBs configuration is expected to be a dictionary")
        selected_stbs = [key for key, details in stbs_dict.items() if details.get('selected') and details.get('is_recent')]
        return selected_stbs

    def run_curl_command(self, command):
        os.chdir(script_dir)
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr

    def request_log_upload(self):
        selected_logs = self.get_selected_logs()
        file_versions_str = self.file_versions_entry.get()
        if file_versions_str.isdigit():
            file_versions = int(file_versions_str)
        else:
            file_versions = 2

        file_ids = self.get_file_ids_for_logs(selected_logs, file_versions)
        file_id_str = ','.join(map(str, file_ids))  # Convert each file_id to a string
        for selected_stb in self.get_selected_stbs():
            upload(selected_stb, file_id_str, self.upload_destination_var.get())

    def get_selected_logs(self):
        selected_indices = self.listbox.curselection()
        selected_logs = [self.listbox.get(i) for i in selected_indices]
        return selected_logs

    def get_file_ids_for_logs(self, names, file_versions):
        file_ids = []
        with open('uploadable_files.json', 'r') as files_file:
            files_data = json.load(files_file)
        with open('uploadable_file_groups.json', 'r') as groups_file:
            groups_data = json.load(groups_file)
        for name in names:
            for group in groups_data:
                if group['name'] == name:
                    group_id = group['id']
                    matching_files = [f['id'] for f in files_data if f['groupId'] == group_id][:file_versions]
                    file_ids.extend(matching_files)
        return file_ids

    def uploadable_files(self):
        curl_command = (f'curl --location "{HOST}/{uploadable_files_path}" '
                        f'--header "Gnat-Authorization-Key: {GNAT_AUTH_KEY}"')
        stdout, stderr = self.run_curl_command(curl_command)
        if stdout:
            try:
                response_data = json.loads(stdout)
                print("Uploadable Files Command Output:", response_data)
                # Save to file
                with open('uploadable_files.json', 'w') as json_file:
                    json.dump(response_data, json_file, indent=4)
            except json.JSONDecodeError:
                print("Failed to decode JSON response.")
        if stderr:
            print("Errors:", stderr)

    def uploadable_file_groups(self):
        curl_command = (f'curl --location "{HOST}/{uploadable_file_groups_path}" '
                        f'--header "Gnat-Authorization-Key: {GNAT_AUTH_KEY}"')
        stdout, stderr = self.run_curl_command(curl_command)
        if stdout:
            try:
                response_data = json.loads(stdout)
                print("Uploadable File Groups Command Output:", response_data)
                # Save to file
                with open('uploadable_file_groups.json', 'w') as json_file:
                    json.dump(response_data, json_file, indent=4)
            except json.JSONDecodeError:
                print("Failed to decode JSON response.")
        if stderr:
            print("Errors:", stderr)

    def load_logs_from_json(self):
        try:
            with open('uploadable_file_groups.json', 'r') as file:
                data = json.load(file)
                names = sorted(group['name'] for group in data)
                for name in names:
                    self.listbox.insert(tk.END, name)
        except Exception as e:
            print(f"Failed to load names from uploadable_file_groups.json: {e}")

    def get_selected_stbs_from_download(self):
        selected_indices = self.download_listbox.curselection()
        selected_stbs = [self.download_listbox.get(i) for i in selected_indices]
        return selected_stbs

    def get_linux_pc_from_config(self):
        with open(config_file, 'r') as file:
            config_data = json.load(file)
        linux_pc = next(iter(config_data['stbs'].values()))['linux_pc']  # Fetch any linux_pc from the config
        return linux_pc

    def check_and_save_ssh_key(self, linux_pc, username, password):
        ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')
        ssh_key_pub_path = f"{ssh_key_path}.pub"

        if not os.path.exists(ssh_key_path):
            # Generate SSH key if it doesn't exist
            subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', ssh_key_path, '-N', ''], check=True)

        # Read the public key
        with open(ssh_key_pub_path, 'r') as pubkey_file:
            public_key = pubkey_file.read().strip()

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(linux_pc, username=username, password=password)
            
            # Check if the key is already added
            stdin, stdout, stderr = ssh.exec_command('cat ~/.ssh/authorized_keys')
            authorized_keys = stdout.read().decode()
            if public_key not in authorized_keys:
                ssh.exec_command(f'echo "{public_key}" >> ~/.ssh/authorized_keys')

            ssh.close()
        except Exception as e:
            print(f"Failed to add SSH key: {e}")

    def get_linux_pc_logs(self, linux_pc, receiver_id, username, password):
        remote_path = f"/ccshare/logs/smplogs/{receiver_id}"
        base_local_path = filedialog.askdirectory(title="Select download location")
        if not base_local_path:
            return
            
        local_path = os.path.join(base_local_path, receiver_id)

        # Establish SSH connection
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(linux_pc, username=username, password=password)

            sftp = ssh.open_sftp()
            self.download_recursive(sftp, remote_path, local_path)
            sftp.close()
            ssh.close()

            # No need to Uncompress downloaded files
            #self.uncompress_files(local_path)
            
            print(f"{receiver_id} downloaded successfully.")
        except Exception as e:
            print(f"Failed to download logs: {e}")

    def download_recursive(self, sftp, remote_path, local_path):
        os.makedirs(local_path, exist_ok=True)
        try:
            entries = sftp.listdir_attr(remote_path)
        except IOError as e:
            print(f"Error accessing {remote_path}: {str(e)}")
            return
        for entry in entries:
            remote_file_path = os.path.join(remote_path, entry.filename).replace('\\', '/')
            sanitized_filename = entry.filename.replace(':', '_')
            local_file_path = os.path.join(local_path, sanitized_filename)

            print(f'Remote location: {remote_file_path}')  # Ensure correct path display
            
            if stat.S_ISDIR(entry.st_mode):
                self.download_recursive(sftp, remote_file_path, local_file_path)
            else:
                try:
                    sftp.get(remote_file_path, local_file_path)
                    print(f"Downloaded {remote_file_path} to {local_file_path}")
                except Exception as e:
                    print(f"Failed to download {remote_file_path}: {str(e)}")

    def uncompress_files(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.gz'):
                    compressed_file = os.path.join(root, file)
                    uncompressed_file = os.path.join(root, file[:-3])  # Remove .gz extension
                    try:
                        with gzip.open(compressed_file, 'rb') as f_in:
                            with open(uncompressed_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        os.remove(compressed_file)
                        print(f"Uncompressed and deleted {compressed_file}")
                    except Exception as e:
                        print(f"Failed to uncompress {compressed_file}: {str(e)}")

    def download_logs(self):
        selected_stbs = self.get_selected_stbs_from_download()
        linux_pc = self.get_linux_pc_from_config()

        credentials = load_credentials()
        username = credentials['username']
        password = credentials['password']

        if not username or not password:
            print("Username and password are required")
            return

        #self.check_and_save_ssh_key(linux_pc, username, password)

        with open(config_file, 'r') as file:
            config_data = json.load(file)

        for stb_name in selected_stbs:
            receiver_id = self.get_receiver_id_from_stb_name(stb_name)
            if receiver_id:
                self.get_linux_pc_logs(linux_pc, receiver_id, username, password)

    def populate_download_listbox(self):
        self.download_listbox.delete(0, tk.END)  # Clear the listbox before populating
        try:
            linux_pc = self.get_linux_pc_from_config()

            credentials = load_credentials()
            username = credentials['username']
            password = credentials['password']

            if not username or not password:
                print("Username and password are required")
                return

            #self.check_and_save_ssh_key(linux_pc, username, password)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(linux_pc, username=username, password=password)

            sftp = ssh.open_sftp()

            selected_stbs = self.get_selected_stbs()
            for stb_name in selected_stbs:
                receiver_id = self.get_receiver_id_from_stb_name(stb_name)
                remote_path = f"/ccshare/logs/smplogs/{receiver_id}"
                try:
                    sftp.listdir(remote_path)  # Check if the directory exists
                    self.download_listbox.insert(tk.END, stb_name)
                except IOError:
                    continue

            sftp.close()
            ssh.close()
        except Exception as e:
            print(f"Failed to populate download listbox: {e}")

    def get_receiver_id_from_stb_name(self, stb_name):
        with open(config_file, 'r') as file:
            config_data = json.load(file)
        stb_details = config_data['stbs'].get(stb_name)
        return stb_details.get('stb')[:11] if stb_details else None

class ToolTip:
    def __init__(self, widget, text, sound_file=None):
        self.widget = widget
        self.text = text
        self.sound_file = sound_file
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, justify=tk.LEFT,
                          background="#333333", foreground="#ffffff",  # Dark background and white text
                          relief=tk.SOLID, borderwidth=1,
                          wraplength=200)
        label.pack(ipadx=1)

        # Play the audio file
        if self.sound_file:
            pygame.mixer.music.load(self.sound_file)
            pygame.mixer.music.play()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

        # Stop the audio when the tooltip is hidden
        if self.sound_file:
            pygame.mixer.music.stop()




if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('800x400')
    app = DebugGUI(master=root)
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False))
    flask_thread.start()
    root.mainloop()