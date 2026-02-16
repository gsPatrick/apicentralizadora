import paramiko
import time

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def run_command(ssh, cmd):
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    # Wait for command to finish
    exit_status = stdout.channel.recv_exit_status()
    
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    
    if out: print(f"STDOUT: {out}")
    if err: print(f"STDERR: {err}")
    
    return exit_status

def sync():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("\n--- UPDATING APIDOIS ---")
    # Check if /opt/apidois exists
    sftp = ssh.open_sftp()
    try:
        sftp.stat("/opt/apidois")
        exists_apidois = True
    except FileNotFoundError:
        exists_apidois = False
    
    if exists_apidois:
        run_command(ssh, "cd /opt/apidois && git pull origin main")
        run_command(ssh, "systemctl restart apidois")
        run_command(ssh, "systemctl status apidois --no-pager")
    else:
        print("/opt/apidois not found. Skipping.")

    print("\n--- UPDATING LEGACY (sbacem-api) ---")
    try:
        sftp.stat("/opt/sbacem-api")
        exists_legacy = True
    except FileNotFoundError:
        exists_legacy = False
        
    if exists_legacy:
        print("Found /opt/sbacem-api. Updating...")
        run_command(ssh, "cd /opt/sbacem-api && git pull")
        run_command(ssh, "systemctl restart sbacem-api")
        run_command(ssh, "systemctl status sbacem-api --no-pager")
    else:
        print("/opt/sbacem-api not found. Skipping.")

    sftp.close()
    ssh.close()
    print("\nSync Complete!")

if __name__ == "__main__":
    sync()
