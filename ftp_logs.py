import ftplib
import os
from datetime import datetime
import paramiko
import time
import tkinter as tk
from scp import SCPClient

def ftp_mkdir_recursive(ftp, remote_dir):
    directories = remote_dir.split('/')
    for dir_part in directories:
        if dir_part:
            try:
                ftp.cwd(dir_part)
                print(f"Changed directory to {dir_part}")
            except ftplib.error_perm:
                try:
                    ftp.mkd(dir_part)
                    ftp.cwd(dir_part)
                    print(f"Created and changed directory to {dir_part}")
                except ftplib.error_perm as e:
                    print(f"Error creating directory {dir_part}: {str(e)}")
                    return False
    return True

def ftp_upload_file(ftp, filepath, remote_path):
    try:
        with open(filepath, 'rb') as file:
            ftp.storbinary(f'STOR {remote_path}', file)
        print(f"Uploaded file: {filepath} to {remote_path}")
    except Exception as e:
        print(f"Error uploading file {filepath}: {str(e)}")

def ftp_upload(local_file, remote_directory, ftp_server, ftp_username, ftp_password):
    try:
        with ftplib.FTP(ftp_server) as ftp:
            ftp.login(user=ftp_username, passwd=ftp_password)
            print(f"Logged in to FTP server {ftp_server}")

            if not ftp_mkdir_recursive(ftp, remote_directory):
                return

            filename = os.path.basename(local_file)
            remote_path = os.path.join(remote_directory, filename).replace("\\", "/")
            print(f"Uploading file {local_file} to {remote_path}")
            ftp_upload_file(ftp, local_file, remote_path)

        print(f"Successfully uploaded {local_file} to FTP server.")
    except Exception as e:
        print(f"FTP upload error: {str(e)}")
