import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def fix():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("Installing Gunicorn...")
    stdin, stdout, stderr = ssh.exec_command("cd /opt/apicentralizadora && ./venv/bin/pip install gunicorn")
    print(stdout.read().decode())
    print(stderr.read().decode())

    print("Restarting Service...")
    ssh.exec_command("systemctl restart apicentralizadora")
    
    print("Checking Status...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status apicentralizadora")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    fix()
