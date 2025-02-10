#!/usr/bin/env python3

import os
import sys
import socket
import requests
import time
import xmltodict
import json
import netifaces
from datetime import datetime

script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary
sys.path.append(script_dir)   ## add this in front of sub process: "  os.chdir(script_dir)  "

KEY = "LOCATION: "
SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 5
SSDP_ST = "urn:schemas-echostar-com:service:EchostarService:1"
FOUND_STBS_FILE = 'found_stbs.json'
config_file = 'base.txt'

def update_stb_ip():
    with open(config_file, 'r') as file:
        config_data = json.load(file)
    with open(FOUND_STBS_FILE, 'r') as file:
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
                break

        '''if not found:
            new_name = f"{model}-{len(config_data['stbs']) + 1}"
            config_data["stbs"][new_name] = {
                'stb': stb,
                'ip': new_ip,
                'model': model,
                'sw_ver': "",
                'protocol': 'SGS',
                'remote': '0',
                "lname": "v0001_client_9830a9879da74b50707792e71dca446da28c3bda",
                "passwd": "35d1ea1fa281ed26a646f4f6b573b90cf1a0d18e",
                "prod": "",
                "linux_pc": "",
                "com_port": "",
                "master_stb": "",
                "rid": ""
            }
            updated = True
            print(f"Added {new_name} with IP {new_ip} and STB {stb}.")'''

    if updated:
        with open(config_file, 'w') as file:
            json.dump(config_data, file, indent=4)



def update_found_stbs(serial_number, ip, model_name):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.chdir(script_dir)
    updated = False
    new_entry = False

    try:
        with open(FOUND_STBS_FILE, 'r') as file:
            found_stbs = json.load(file)
    except FileNotFoundError:
        found_stbs = {}
        new_entry = True

    if serial_number in found_stbs:
        old_ip = found_stbs[serial_number]['ip']
        if old_ip != ip:
            found_stbs[serial_number]['ip'] = ip
            updated = True
            print(f"@ {current_time} Updating {serial_number} from {old_ip} to {ip}")
    else:
        new_entry = True

    if new_entry:
        found_stbs[serial_number] = {
            'ip': ip,
            'model': model_name,
            'stb': serial_number
        }
        print(f"@ {current_time} Found {serial_number} at {ip}")

    with open(FOUND_STBS_FILE, 'w') as file:
        json.dump(found_stbs, file, indent=4)
        
    update_stb_ip()

    return updated

def send_ssdp_request(interface):
    ssdp_request = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        f"MX: {SSDP_MX}\r\n"
        f"ST: {SSDP_ST}\r\n"
        "\r\n"
    )
    data_bytes = bytearray(ssdp_request, 'utf-8')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    sock.settimeout(2)
    sock.sendto(data_bytes, (SSDP_ADDR, SSDP_PORT))

    return sock

while True:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"-------------------{current_time}--------------------------")
    
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                #print(f"Checking interface with IP {ip}")
                sock = send_ssdp_request(ip)

                while True:
                    try:
                        data = sock.recv(2000)
                    except socket.timeout:
                        break

                    lines = data.decode("utf-8").split("\r\n")
                    location = [x[len(KEY):] for x in lines if x.startswith(KEY)][0]
                    #print("location:", location)

                    stb_info = xmltodict.parse(requests.get(location).content)
                    serial_number = stb_info["root"]["device"]["serialNumber"]
                    ip = location[len("http://"):-len("/device.xml")].split(':')[0]
                    model_name = stb_info["root"]["device"]["modelName"]

                    #print(f"RID: {serial_number}, ip: {ip:15}, name: {model_name}")

                    # Update the found_stbs.json file
                    update_found_stbs(serial_number, ip, model_name)

    print()

    time.sleep(10)
