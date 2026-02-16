import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def run_cmd(ssh, cmd):
    print(f"\n>>> Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"STDOUT:\n{out}")
    if err: print(f"STDERR:\n{err}")

def diagnose():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("\n=== CHECKING DIRECTORY STRUCTURE ===")
    run_cmd(ssh, "ls -la /opt/apicentralizadora")
    run_cmd(ssh, "ls -la /opt/apicentralizadora/app 2>/dev/null || echo 'App dir not found'")
    
    print("\n=== CHECKING SERVICE STATUS ===")
    run_cmd(ssh, "systemctl status apicentralizadora --no-pager")
    run_cmd(ssh, "systemctl status apidois --no-pager")
    run_cmd(ssh, "systemctl status sbacem-api --no-pager")

    print("\n=== CHECKING LISTENING PORTS ===")
    run_cmd(ssh, "ss -tulpn | grep -E '8001|8002|8003'")
    
    print("\n=== CHECKING LOGS (Last 50 lines for apicentralizadora) ===")
    run_cmd(ssh, "journalctl -u apicentralizadora -n 50 --no-pager")

    ssh.close()

if __name__ == "__main__":
    diagnose()
