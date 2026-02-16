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
    
    sftp = ssh.open_sftp()
    SITE_FILE = "/etc/nginx/sites-available/sbacem-api"
    
    try:
        with sftp.file(SITE_FILE, "r") as f:
            print(f"--- CONTENT OF {SITE_FILE} ---")
            print(f.read().decode())
            print("--- END OF FILE ---")
    except Exception as e:
        print(f"Error reading file: {e}")

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    debug()
