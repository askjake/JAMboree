import socket
import subprocess
import json
import re
import os
import ipaddress
import platform
import sys

script_dir = os.path.abspath('scripts/')
sys.path.append(script_dir)
config_file = 'base.txt'
backup_config_file = 'base_back.txt'

def ping_ip(ip):
    param = '-n' if sys.platform.lower() == 'win32' else '-c'
    command = ['ping', param, '1', ip]
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        return True  # IP is alive
    except subprocess.CalledProcessError:
        return False  # IP is not alive

def get_subnets_from_arp():
    subnets = set()
    system = platform.system()

    if system == 'Windows':
        arp_command = ['arp', '-a']
    elif system == 'Linux':
        arp_command = ['arp', '-n']
    else:
        print(f"Unsupported system: {system}")
        return set()

    try:
        output = subprocess.check_output(arp_command, universal_newlines=True)
        lines = output.split('\n')
        for line in lines:
            parts = line.split()
            ip_field = 1 if system == 'Windows' else 0
            if len(parts) > ip_field and parts[ip_field].count('.') == 3:
                ip = parts[ip_field].strip('()')
                try:
                    ip_obj = ipaddress.ip_address(ip)
                    if ip_obj.is_multicast or (224 <= int(ip_obj.packed[0]) <= 239) or (169 == int(ip_obj.packed[0])) or (255 == int(ip_obj.packed[0])):
                        continue  # Skip multicast or reserved address
                    network = ipaddress.ip_network(f'{ip}/24', strict=False)
                    subnets.add(network)
                    supernet = network.supernet()
                    adjacent_subnets = list(supernet.subnets())
                    if network in adjacent_subnets:
                        index = adjacent_subnets.index(network)
                        if index > 0:
                            subnets.add(adjacent_subnets[index - 1])
                        if index + 1 < len(adjacent_subnets):
                            subnets.add(adjacent_subnets[index + 1])
                except ValueError:
                    continue
    except subprocess.CalledProcessError:
        print("Failed to get subnets from ARP table on", system)

    # Load additional subnets from the config file
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            try:
                config_data = json.load(file)
                for stb_name, stb_details in config_data.get("stbs", {}).items():
                    ip = stb_details.get("ip", "")
                    if ip:
                        try:
                            ip_obj = ipaddress.ip_address(ip)
                            network = ipaddress.ip_network(f'{ip}/24', strict=False)
                            subnets.add(network)
                        except ValueError:
                            continue
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from config file: {config_file}")

    return subnets

def discover_ips(subnets):
    print(f"Discovering IPs: {subnets}")
    ip_list = []
    for subnet_str in subnets:
        subnet = ipaddress.ip_network(subnet_str)
        for ip in subnet.hosts():
            ip_str = str(ip)
            try:
                sock = socket.create_connection((ip_str, 443), timeout=0.01)
                sock.close()
                ip_list.append(ip_str)
            except:
                pass
    return ip_list

def do_ips(ip):
    os.chdir(script_dir)
    if ping_ip(ip): 
        try:
            command = ["python", "get_stb_information.py", "-i", ip, "-v"]
            output = subprocess.check_output(command, universal_newlines=True)

            # Extract all JSON data from "--- response" lines
            json_objects = []
            for line in output.splitlines():
                if '--- response:' in line:
                    json_str = line.split('--- response:')[1].strip()
                    try:
                        json_obj = json.loads(json_str)
                        json_objects.append(json_obj)
                    except json.JSONDecodeError as e:
                        #print(f"Failed to parse JSON from response line for IP {ip}: {str(e)}")
                        continue

            # Check if any JSON objects were found
            if not json_objects:
                #print(f"No JSON response found in output for IP {ip}.")
                return f"No JSON response found in output for IP {ip}.\n"

            # Assuming we're interested in the first valid JSON object found
            stb_info = json_objects[0].get('data', {})

            if not stb_info:
                #print(f"No 'data' key found in JSON response for IP {ip}: {json_objects[0]}")
                return f"No 'data' key found in JSON response for IP {ip}: {json_objects[0]}\n"

            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in file {config_file}: {str(e)}")
                return

            # Handle the extracted data
            if 'rxid' in stb_info:
                rxid = stb_info['rxid']
                
                # Check if this rxid already exists in the config
                existing_entry = None
                stb_name = None
                for name, entry in config_data["stbs"].items():
                    if entry.get("stb") == rxid:
                        existing_entry = entry
                        stb_name = name
                        break

                if existing_entry:
                    old_ip = existing_entry.get('ip', 'N/A')
                    existing_entry['ip'] = ip
                    existing_entry.update({
                        'model': stb_info.get('model', ''),
                        'sw_ver': stb_info.get('sw_ver', ''),
                        'apps': stb_info.get('web_app_swid', ''),
                    })
                    with open(config_file, 'w') as file:
                        json.dump(config_data, file, indent=4)

                    if old_ip != ip:
                        print(f"Updated {rxid} from IP {old_ip} to {ip}.")
                        return f"Updated {rxid} from IP {old_ip} to {ip}.\n"
                else:
                    new_name = f"{stb_info['model']}-{len(config_data['stbs']) + 1}"
                    config_data["stbs"][new_name] = {
                        'stb': rxid,
                        'smartcard_id': stb_info.get('smartcard_id', ''),
                        'ip': ip,
                        'model': stb_info.get('model', ''),
                        'sw_ver': stb_info.get('sw_ver', ''),
                        'hwid': stb_info.get('hwid', ''),
                        'apps': stb_info.get('web_app_swid', ''),
                        'transceiver_fwid': stb_info.get('transceiver_fwid', ''),
                        'nbiot_swid': stb_info.get('nbiot_swid', ''),
                        'protocol': 'SGS',
                        'remote': '0',
                        "lname": "",
                        "passwd": "",
                        "linux_pc": "",
                        "com_port": "",
                        "master_stb": "",
                        "selected": "",
                        "rid": stb_info.get('rxid', '')
                    }
                    with open(config_file, 'w') as file:
                        json.dump(config_data, file, indent=4)
                    print(f"Added {rxid} with IP {ip} as {new_name}.")
                    return f"Added {rxid} with IP {ip} as {new_name}.\n"
        except subprocess.CalledProcessError as e:
            print(f"Failed to get STB information for IP {ip}: {str(e)}")
            return f"Failed to get STB information for IP {ip}: {str(e)}\n"
    else:
        #print(f"IP {ip} is not reachable.")
        return f"IP {ip} is not reachable.\n"
        
if __name__ == '__main__':
    os.chdir(script_dir)
    config_file = 'base.txt'
    backup_config_file = 'base_back.txt'
    subnets = get_subnets_from_arp()
    ips = discover_ips(subnets)
    for ip in ips:
        do_ips(ip)
