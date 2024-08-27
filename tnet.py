import os
import sys
import logging
import telnetlib
import paramiko
from time import sleep

logging.basicConfig(level=logging.DEBUG)
tnet_version = "1.20"

# User customizable variables - Customize this for your setup
nfs_top_dir = f""

def run_telnet(ip, stb_dir, web_app=None, cmd=None, mount_nand=0):
    logging.info(f"tnet script version: {tnet_version}")

    if not ip or not stb_dir:
        print("Usage: tnet <ip address> <mount_point> <web_app> [kill command] [mount NAND:0-no,1-yes]")
        sys.exit(1)

    telnet = telnetlib.Telnet(ip)
    mount_opts = "-o soft,nolock,tcp,rsize=1024,wsize=1024"
    unmount_cmd = "umount -l /usr/local /var/mnt/drivers\n"
    mount_cmd = f"mount {mount_opts} {ip}:{nfs_top_dir}{stb_dir} /mnt/mine\n"
    export_cmd = "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH\n cd /mnt/mine/ \n ls -l\n"
    prompt = "~ #"

    # Telnet Login
    for _ in range(120):
        try:
            telnet.read_until(b"login: ")
            telnet.write(b"root\n")
            if cmd:
                telnet.write(cmd.encode('ascii') + b"\n")
            break
        except EOFError:
            logging.warning("Connection timed out. Retrying...")
            sleep(2)
            continue

    # Execute the necessary commands
    telnet.read_until(prompt.encode('ascii'))
    telnet.write(unmount_cmd.encode('ascii'))
    telnet.read_until(prompt.encode('ascii'))
    telnet.write(mount_cmd.encode('ascii'))
    telnet.read_until(prompt.encode('ascii'))
    telnet.write(export_cmd.encode('ascii'))

    # Execute untar command if web_app is provided
    if web_app:
        untar_cmd = f"tar -xvzf {web_app} -C /mnt/MISC_HD\n"
        telnet.read_until(prompt.encode('ascii'))
        telnet.write(untar_cmd.encode('ascii'))

    # Try to mount NAND on Wally
    if mount_nand == 1:
        telnet.read_until(prompt.encode('ascii'))
        telnet.write(b"mount -t squashfs /dev/mtdblock3 /mnt/drivers\n")
        telnet.read_until(prompt.encode('ascii'))
        telnet.write(b"insmod /lib/modules/sdhci-brcmstb.ko\n")
        telnet.read_until(prompt.encode('ascii'))
        telnet.write(b"mount -t ext4 /dev/mmcblk0p1 /var/mnt/NAND\n")

    telnet.write(b"exit\n")
    telnet.close()

def run_ssh(ip, stb_dir, web_app=None, cmd=None, mount_nand=0):
    logging.info(f"tnet script version: {tnet_version}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username='root', password='')

    mount_opts = "-o soft,nolock,tcp,rsize=1024,wsize=1024"
    unmount_cmd = "umount -l /usr/local /var/mnt/drivers"
    mount_cmd = f"mount {mount_opts} {ip}:{nfs_top_dir}{stb_dir} /mnt/mine"
    export_cmd = "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH && cd /mnt/mine/ && ls -l"

    # Run commands via SSH
    commands = [unmount_cmd, mount_cmd, export_cmd]
    if web_app:
        commands.append(f"tar -xvzf {web_app} -C /mnt/MISC_HD")
    if mount_nand == 1:
        commands.extend([
            "mount -t squashfs /dev/mtdblock3 /mnt/drivers",
            "insmod /lib/modules/sdhci-brcmstb.ko",
            "mount -t ext4 /dev/mmcblk0p1 /var/mnt/NAND"
        ])

    for command in commands:
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            logging.info(f"Output from command '{command}':\n{output}")
        if error:
            logging.error(f"Error from command '{command}':\n{error}")

    ssh.close()

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 6:
        print("Usage: tnet <ip address> <mount_point> <web_app> [kill command] [mount NAND:0-no,1-yes]")
        sys.exit(1)

    ip = sys.argv[1]
    stb_dir = sys.argv[2]
    web_app = sys.argv[3] if len(sys.argv) > 3 else None
    cmd = sys.argv[4] if len(sys.argv) > 4 else None
    mount_nand = int(sys.argv[5]) if len(sys.argv) > 5 else 0

    try:
        run_telnet(ip, stb_dir, web_app, cmd, mount_nand)
    except Exception as e:
        logging.error(f"Telnet failed: {e}")
        logging.info("Attempting to run via SSH instead...")
        run_ssh(ip, stb_dir, web_app, cmd, mount_nand)

if __name__ == "__main__":
    main()
