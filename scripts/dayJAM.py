import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime, timedelta
import subprocess
import glob
import threading
import paramiko
import os
import sys
import sched
import select
import time
from tkinter import PhotoImage

credentials_file = 'credentials.json'
config_file = 'base.txt'
apps_dir = os.path.abspath('apps/')  # Adjust this path as necessary
linux_pc_apps = '/home/diship/stbmnt/apps/'
linux_pc_stbmnt = '/home/diship/stbmnt/'

sys.path.append(apps_dir)

class SetTopJAM(tk.Frame):  # Ensure it's a Frame subclass
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill='both', expand=True)
        self.linux_pc_var = tk.StringVar()
        self.release_name_var = tk.StringVar()
        self.entries = []
        self.config_file = 'settops.json'
        self.remote_path = '/ccshare/linux/c_files/signed-browser-applications/internal'
        self.local_apps = 'apps'
        self.linux_pc_apps = linux_pc_apps
        
        self.setup_ui()
        self.load_config()        
        
        # Load file list from JSON and populate STB list on start
        self.load_file_list_from_json()
        self.populate_stb_list()
        
        self.after(1000, self.automate)

    def setup_ui(self):
        tk.Label(self, text='Linux PC').grid(row=0, column=0)
        tk.Entry(self, textvariable=self.linux_pc_var).grid(row=0, column=1)
        
        self.automate_var = tk.BooleanVar()
        self.automate_check = tk.Checkbutton(self, text='dayJAM', variable=self.automate_var)
        self.automate_check.grid(row=1, column=2)
    
        tk.Label(self, text='At: HH:MM').grid(row=1, column=0)
        self.start_time_var = tk.StringVar()
        self.start_time_entry = tk.Entry(self, textvariable=self.start_time_var)
        self.start_time_entry.grid(row=1, column=1)

        for i in range(10):
            tk.Label(self, text=f'{i+1}. stb-ip:').grid(row=i+2, column=0)
            entry = tk.Entry(self)
            entry.grid(row=i+2, column=1)
            self.entries.append(entry)
            
        # Listbox for file selection
        self.file_listbox = tk.Listbox(self, height=10, width=50, exportselection=False)
        self.file_listbox.grid(row=13, column=0, columnspan=3, pady=20)

        # Listbox for STB selection
        self.stb_listbox = tk.Listbox(self, height=10, width=50, exportselection=False)
        self.stb_listbox.grid(row=13, column=3, columnspan=3, pady=20)

        self.refresh_button = tk.Button(self, text='Refresh', command=self.populate_lists)
        self.refresh_button.grid(row=12, column=0)

        self.load_apps_button = tk.Button(self, text='Load my APPs', command=self.load_apps)
        self.load_apps_button.grid(row=12, column=1)

        self.output_text = tk.Text(self, height=10, width=100)
        self.output_text.grid(row=14, column=0, columnspan=6, pady=20)

    @staticmethod
    def round_time(dt, delta):
        """
        Rounds the time to the nearest 'delta' minutes.
        """
        round_to = delta.total_seconds()
        seconds = (dt - dt.min).seconds
        rounding = (seconds + round_to / 2) // round_to * round_to
        return dt + timedelta(0, rounding - seconds, -dt.microsecond)
        
    def automate(self):
        if self.automate_var.get():  # If the automation checkbox is checked
            now = datetime.now()
            start_time = datetime.strptime(self.start_time_var.get(), '%H:%M').replace(year=now.year, month=now.month, day=now.day)
            if start_time < now: 
                start_time += timedelta(days=1)
            delay = (start_time - now).total_seconds()
            
            def task():
                self.start_jam_threaded()
                self.after(1000, self.automate)  # Reschedule automate after the task to make it run daily

            threading.Timer(delay, task).start()  # Use threading.Timer to wait for the 

    def start_jam_threaded(self):
        self.start_button["state"] = "disabled"
    
        for i in range(min(10, len(self.entries))):  # Start a thread for each entry, up to 10
            self.start_jam(i)
        self.start_button["state"] = "normal"
        
    def get_linux_pc_from_config(self):
        with open(config_file, 'r') as file:
            config_data = json.load(file)
        linux_pc = next(iter(config_data['stbs'].values()))['linux_pc']  # Fetch any linux_pc from the config
        return linux_pc

    def start_jam(self, thread_index):
        stb_ip = self.entries[thread_index].get()  # Simplified example
        linux_pc = self.get_linux_pc_from_config()

        if stb_ip:  
            update_successful = self.dva(stb_ip, linux_pc)
            now = datetime.now()
            rounded_time = self.round_time(now, timedelta(minutes=15))
            timestamp = rounded_time.strftime("%Y-%m-%d %H:%M")

            if update_successful:
                # Make sure to synchronize access to shared resources like GUI components
                self.output_text.insert(tk.END, f"{timestamp} {stb_ip} BOOM\n")
            else:
                self.output_text.insert(tk.END, f"{timestamp} {stb_ip} DUDD\n")
            self.output_text.see(tk.END)
            
        self.save_config()
        self.start_button["state"] = "normal"
        
    def save_jam(self):
        self.save_config()
    
    def save_config(self):
        settings = []
        for entry in self.entries:
            stb_ip = entry.get()
            if stb_ip:  # Assuming you want to save only entries with IP filled
                settings.append({'stb_ip': stb_ip})

        config_data = {
            'linux_pc': self.linux_pc_var.get(),
            'release_name': self.release_name_var.get(),
            'settings': settings,
            'automate_enabled': self.automate_var.get(),
            'start_time': self.start_time_var.get()
        }
    
        with open(self.config_file, 'w') as file:
            json.dump(config_data, file, indent=4)

    def load_config(self):
        try:
            with open(self.config_file, 'r') as file:
                data = json.load(file)
                self.linux_pc_var.set(data.get('linux_pc', ''))
                self.release_name_var.set(data.get('release_name', ''))
                self.automate_var.set(data.get('automate_enabled', False))
                self.start_time_var.set(data.get('start_time', ''))
                settings = data.get('settings', [])
                for i, setting in enumerate(settings):
                    if i < len(self.entries):
                        self.entries[i].delete(0, tk.END)
                        self.entries[i].insert(0, setting.get('stb_ip', ''))
        except FileNotFoundError:
            print("Config file not found, loading defaults.")
    
    def update_output(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
            
    def dva(self, stb_ip, linux_pc):
        update_successful = False
        now = datetime.now()
        rounded_time = self.round_time(now, timedelta(minutes=15))
        timestamp = rounded_time.strftime("%Y-%m-%d %H:%M")
        print(f"{timestamp}: JAMming")
        print(f"stb_ip: {stb_ip}")
        print(f"linux_pc: {linux_pc}")
        self.output_text.insert(tk.END, f"{timestamp} {stb_ip} JAMming \n")
        self.output_text.see(tk.END)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(linux_pc, username='diship', password='Dish1234')
        
            # Execute the command and wait for it to complete
            command = f"~/dish-virtual-assistant/bin/dish-virtual-assistant jam -d -t {stb_ip}"
            stdin, stdout, stderr = ssh.exec_command(command)

            # This is a blocking call that waits until the command has completed
            output = stdout.read().decode()
            error = stderr.read().decode()
        
            if error:
                print(f"Error: {error}")
            else:
                if "successfully jammed" in output:
                    update_successful = True
                print(output)

            ssh.close()
        except Exception as e:
            print(f"SSH connection error: {e}")
    
        return update_successful

    def populate_lists(self):
        self.populate_file_list()
        self.populate_stb_list()

    def load_file_list_from_json(self):
        apps_list_file = 'apps_list.json'
        if os.path.exists(apps_list_file):
            try:
                with open(apps_list_file, 'r') as json_file:
                    apps_list = json.load(json_file)
                    self.file_listbox.delete(0, tk.END)
                    for file in apps_list:
                        self.file_listbox.insert(tk.END, f"{file['date']} - {file['filename']}")
                    self.update_output(f"File list loaded from {apps_list_file}.")
            except Exception as e:
                self.update_output(f"Failed to load file list from {apps_list_file}: {e}")
        else:
            self.update_output(f"{apps_list_file} not found. Consider refreshing the list.")

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
                if file.filename.startswith('AN'):
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

    def populate_stb_list(self):
        self.stb_listbox.delete(0, tk.END)  # Clear the STB listbox before populating
        try:
            with open(config_file, 'r') as file:
                config_data = json.load(file)
                stbs = config_data.get('stbs', {})
                for stb_name in stbs:
                    self.stb_listbox.insert(tk.END, stb_name)
        except Exception as e:
            self.update_output(f"Failed to populate STB list: {e}")

    def load_apps(self):
        try:
            selected_file_index = self.file_listbox.curselection()
            selected_stb_index = self.stb_listbox.curselection()

            if not selected_file_index or not selected_stb_index:
                self.update_output("Please select both a file and an STB.")
                return

            selected_file = self.file_listbox.get(selected_file_index)
            selected_stb = self.stb_listbox.get(selected_stb_index)
            
            with open(config_file, 'r') as file:
                config_data = json.load(file)
                stbs = config_data.get('stbs', {})
                stb_ip = stbs.get(selected_stb, {}).get('ip', None)
                if not stb_ip:
                    self.update_output(f"Failed to find IP for STB: {selected_stb}")
                    return

            linux_pc = self.get_linux_pc_from_config()
            credentials = load_credentials()
            username = credentials['username']
            password = credentials['password']

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(linux_pc, username=username, password=password)
            sftp = ssh.open_sftp()

            # Extract the app without the date
            app = selected_file.split(' - ')[1]
            cc_share = f"{self.remote_path}/{app}"
            local_apps = os.path.join(self.local_apps, app)
            linux_pc_app = f"{linux_pc_apps}{app}"
            
            print(f"app: {app}")
            print(f"cc_share: {cc_share}")
            print(f"local_apps: {local_apps}")
            print(f"linux_pc_apps: {linux_pc_apps}")
            
                        
            if not os.path.exists(self.local_apps):
                os.makedirs(self.local_apps)


            if not os.path.exists(local_apps):
                # Download the file if it doesn't exist
                sftp.get(cc_share, local_apps)
                self.update_output(f"Copied {app} to {local_apps}")
            else:
                self.update_output(f"{app} already local at {local_apps}, skipping download.")


            # Upload the file to the linux_pc's /stbmnt/apps/ directory if it doesn't exist there
            try:
                sftp.stat(linux_pc_app)  # Check if file exists on linux_pc
                self.update_output(f"{app} already exists on {linux_pc} at {linux_pc_app}, skipping upload.")
            except FileNotFoundError:
                try:
                    sftp.put(local_apps, linux_pc_app)
                    self.update_output(f"Copied {app} to {linux_pc}:{linux_pc_app}")
                except Exception as upload_error:
                    self.update_output(f"Failed to upload {app} to {linux_pc}:{linux_pc_app}: {upload_error}")
                    return

            sftp.close()
            ssh.close()
            
            self.update_output(f"Now I will put {app} on {selected_stb}")
            self.linux_tnet(linux_pc, stb_ip, app)

        except Exception as e:
            self.update_output(f"Failed to load app: {e}")

    def linux_tnet(self, linux_pc, stb_ip, app):
        try:
            self.update_output("Starting linux_tnet function...")  # Debugging statement
            credentials = load_credentials()
            username = credentials['username']
            password = credentials['password']
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            untar_cmd = f"tar -xvzf {app} -C /mnt/MISC_HD"
            remove_tar = f"rm {app}"
            untar_sent = False
        
            self.update_output("Connecting to Linux PC via SSH...")  # Debugging statement
            ssh.connect(linux_pc, username=username, password=password)
            
            

            self.update_output("Proceeding with the tnet command...")  # Debugging statement
            command = f"cd {linux_pc_stbmnt} && ./tnet {stb_ip} apps"
            self.update_output(f"Running command: {command}")  # Debugging statement
            stdin, stdout, stderr = ssh.exec_command(command)

            untar_cmd = f"tar -xvzf /mnt/mine/{app} -C /mnt/MISC_HD"
            untar_sent = False

            while True:
                # Use select to wait for data to be available
                ready, _, _ = select.select([stdout.channel], [], [], 5.0)
                if ready:
                    line = stdout.readline().strip()
                    if line:
                        self.update_output(f"tnet output: {line}")  # Debugging statement
                        print(f"{line}")  # Debugging statement

                    # Detect the prompt and send the untar command
                    if "/mnt/mine/" in line:
                        time.sleep(1)
                        if not untar_sent:
                            self.update_output("Detected prompt, sending untar command...")  # Debugging statement
                            stdin, stdout, stderr = ssh.exec_command(untar_cmd)
                            untar_sent = True
                            self.update_output(f"Running untar command: {untar_cmd}")  # Debugging statement

                else:
                    # If nothing is ready, break the loop if untar was sent
                    if untar_sent:
                        self.update_output("No more lines to read, breaking out of loop...")  # Debugging statement
                        break

            error = stderr.read().decode('utf-8')
            if error:
                self.update_output(f"Error from tnet command: {error}")  # Debugging statement

            self.update_output("Closing SSH connection...")  # Debugging statement
            ssh.close()
            self.update_output("linux_tnet function completed.")  # Debugging statement
        except Exception as e:
            self.update_output(f"Failed to run linux_tnet or execute commands on STB {stb_ip}: {e}")

def load_credentials():
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as file:
            return json.load(file)
    return {'username': '', 'password': ''}

if __name__ == '__main__':
    root = tk.Tk()
    app = SetTopJAM(master=root)
    app.mainloop()