import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def update():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("Pulling latest changes...")
    ssh.exec_command("cd /opt/apicentralizadora && git pull")
    
    print("Restarting Service...")
    ssh.exec_command("systemctl restart apicentralizadora")
    
    print("Checking Status...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status apicentralizadora --no-pager")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    update()
