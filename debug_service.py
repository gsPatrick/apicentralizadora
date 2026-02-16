import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def debug():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("--- SERVICE STATUS ---")
    stdin, stdout, stderr = ssh.exec_command("systemctl status apicentralizadora")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print("--- RECENT LOGS ---")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u apicentralizadora -n 20 --no-pager")
    print(stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    debug()
