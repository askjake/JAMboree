import telnetlib
import socket
import sys
import os

tnet_version = "1.10"
nfs_top_dir = '/'

def get_host_ip(stb_ip):
    """Get the local IP address associated with a given remote IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((stb_ip, 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Failed to determine local IP address: {e}")
        sys.exit(1)

def run_tnet(ip, stb_dir, kill_command=None, mount_nand=False):
    try:
        # Determine the host IP address for the interface used to reach the STB
        ip_address = get_host_ip(ip)
        print(f"Using host IP address: {ip_address}")

        # Open a Telnet session
        telnet = telnetlib.Telnet(ip)

        # Log in
        output = telnet.read_until(b"login: ")
        print(output.decode('ascii'))
        telnet.write(b"root\n")
        output = telnet.read_until(b"# ")
        print(output.decode('ascii'))

        # Optionally send the kill command
        if kill_command:
            telnet.write(kill_command.encode('ascii') + b"\n")
            output = telnet.read_until(b"# ")
            print(output.decode('ascii'))

        # Unmount existing mounts
        unmount_cmds = [
            "umount -l /usr/local",
            "umount -l /var/mnt/drivers"
        ]
        for unmount_cmd in unmount_cmds:
            telnet.write(unmount_cmd.encode('ascii') + b"\n")
            output = telnet.read_until(b"# ")
            print(output.decode('ascii'))

        # Mount the NFS directory
        mount_opts = "-o soft,nolock,tcp,rsize=1024,wsize=1024"
        mount_cmd = f"mount {mount_opts} {ip_address}:{nfs_top_dir}{stb_dir} /mnt/mine"
        telnet.write(mount_cmd.encode('ascii') + b"\n")
        output = telnet.read_until(b"# ")
        print(output.decode('ascii'))

        # Set environment and change directory
        export_cmd = "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH"
        telnet.write(export_cmd.encode('ascii') + b"\n")
        output = telnet.read_until(b"# ")
        print(output.decode('ascii'))
        
        telnet.write(b"cd /mnt/mine/\n")
        output = telnet.read_until(b"# ")
        print(output.decode('ascii'))

        # Optionally mount NAND on Wally
        if mount_nand:
            nand_cmds = [
                "mount -t squashfs /dev/mtdblock3 /mnt/drivers",
                "insmod /lib/modules/sdhci-brcmstb.ko",
                "mount -t ext4 /dev/mmcblk0p1 /var/mnt/NAND"
            ]
            for nand_cmd in nand_cmds:
                telnet.write(nand_cmd.encode('ascii') + b"\n")
                output = telnet.read_until(b"# ")
                print(output.decode('ascii'))

        telnet.write(b"exit\n")
        telnet.close()

    except Exception as e:
        print(f"Failed to connect or execute commands on STB {ip}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print("Usage: tnet.py <STB_IP_ADDRESS> <NFS_MOUNT_POINT> [Kill Command] [Mount NAND: 0-no, 1-yes]")
        print("Example: tnet.py 192.168.1.202 delta")
        print("Example: tnet.py 192.168.1.202 Wally \"killall -9 stb_run\"")
        print("Example: tnet.py 192.168.1.202 Wally \"killall -9 stb_run\" 1")
        sys.exit(1)

    ip = sys.argv[1]
    stb_dir = sys.argv[2]
    kill_cmd = sys.argv[3] if len(sys.argv) > 3 else None
    mount_nand = bool(int(sys.argv[4])) if len(sys.argv) > 4 else False

    run_tnet(ip, stb_dir, kill_cmd, mount_nand)
