import socket
import subprocess
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import platform
import sys
import ipaddress
import os



script_dir = os.path.abspath('scripts/')  # Adjust this path as necessary
sys.path.append(script_dir)   ## add this in front of sub process: "  os.chdir(script_dir)  "
config_file = 'base.txt'

# Argument parsing
parser = argparse.ArgumentParser(description='Scan IPs and get STB information.')
args = parser.parse_args()
 
  
def ping_ip(ip):
    #print(f'pinging: {ip}')
    param = '-n' if sys.platform.lower() == 'win32' else '-c'
    command = ['ping', param, '1', ip]
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        return True  # IP is alive
    except subprocess.CalledProcessError:
        return False  # IP is not alive
        
import subprocess
import ipaddress
import platform

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
            if len(parts) > ip_field and parts[ip_field].count('.') == 3:  # Simple check to see if it looks like an IP address
                ip = parts[ip_field].strip('()')
                try:
                    ip_obj = ipaddress.ip_address(ip)
                    if ip_obj.is_multicast or (224 <= int(ip_obj.packed[0]) <= 239) or (169 == int(ip_obj.packed[0])) or (255 == int(ip_obj.packed[0])):
                        continue  # Skip the IP if it is a multicast or reserved address
                    network = ipaddress.ip_network(f'{ip}/24', strict=False)
                    subnets.add(network)
                    # Calculate and add adjacent subnets
                    supernet = network.supernet()
                    # Get the previous and next subnet within the supernet's scope
                    adjacent_subnets = list(supernet.subnets())
                    if network in adjacent_subnets:
                        index = adjacent_subnets.index(network)
                        if index > 0:
                            subnets.add(adjacent_subnets[index - 1])  # Add the subnet directly below
                        if index + 1 < len(adjacent_subnets):
                            subnets.add(adjacent_subnets[index + 1])  # Add the subnet directly above
                        if index + 2 < len(adjacent_subnets):
                            subnets.add(adjacent_subnets[index + 2])  # Add the subnet directly above
                except ValueError:
                    continue
    except subprocess.CalledProcessError:
        print("Failed to get subnets from ARP table on", system)

    return subnets

    
def discover_ips(subnets):
    print(f"Discovering IPs: {subnets}")
    ip_list = []
    for subnet_str in subnets:
        subnet = ipaddress.ip_network(subnet_str)  # Convert string to IPv4Network object
        for ip in subnet.hosts():  # Iterate over all usable hosts in the subnet
            ip_str = str(ip)
            try:
                # Attempt to open a socket connection on a common port
                sock = socket.create_connection((ip_str, 443), timeout=0.01)
                sock.close()
                ip_list.append(ip_str)
            except:
                pass
    return ip_list



def do_ips(ip):
            
    #print(f"Processing IP: {ip}")
    os.chdir(script_dir)    
    if ping_ip(ip): 
        try:
            command = ["python", "get_stb_information.py", "-i", ip]
            #print(f"doing: {command}")
            output = subprocess.check_output(command, universal_newlines=True)
            stb_info = {}
            for line  in output.splitlines():
                if "rxid" in line:
                    stb_info['rxid'] = line.split()[2]
                if "model" in line:
                    stb_info['model'] = line.split()[2]
                if "sw_ver" in line:
                    stb_info['sw_ver'] = line.split()[2]
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in file {config_file}: {str(e)}")
                # Handle or log error, maybe load a backup config
                return

        
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

                
                '''
                old_ip = config_data['stbs'].get("ip")
                stb_name = config_data['stbs']
                existing_entry = next((s for s in config_data["stbs"].values() if s.get("stb") == rxid), None)
            '''
            
                if existing_entry:
                    old_ip = existing_entry.get('ip', 'N/A')
                    existing_entry['ip'] = ip  # Update IP address
                    existing_entry.update({
                        'model': stb_info.get('model', ''),
                        'sw_ver': stb_info.get('sw_ver', ''),
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
                        'ip': ip,
                        'model': stb_info.get('model', ''),
                        'sw_ver': stb_info.get('sw_ver', ''),
                        'protocol': 'SGS',
                        'remote': '0',
                        "lname": "",
                        "passwd": "",
                        "linux_pc": "",
                        "com_port": "",
                        "master_stb": "",
                        "selected": "",
                        "rid": ""
                    }
                    with open(config_file, 'w') as file:
                        json.dump(config_data, file, indent=4)
                    print(f"Added {rxid} with IP {ip} as {new_name}.")
                    return f"Added {rxid} with IP {ip} as {new_name}.\n"
        except subprocess.CalledProcessError as e:
            print(f"Failed to get STB information for IP {ip}: {str(e)}")
            return f"Failed to get STB information for IP {ip}: {str(e)}\n"
        #except json.JSONDecodeError:
        #    print(f"Error decoding JSON from output for IP {ip}.")
        #    return f"Error decoding JSON from output for IP {ip}.\n"
    #else:
    #    print(f"IP {ip} is not reachable.")
    #    return f"IP {ip} is not reachable.\n"


if __name__ == '__main__':
    os.chdir(script_dir)
    config_file = 'base.txt'  # Ensure you have the correct path to your config file
    subnets = get_subnets_from_arp()
    ips = discover_ips(subnets)
    for ip in ips:
        do_ips(ip)