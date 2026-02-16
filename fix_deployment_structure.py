import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"
REPO_URL = "https://github.com/gsPatrick/apicentralizadora.git"
REMOTE_DIR = "/opt/apicentralizadora"

# Updated Service Content (Flat structure)
SERVICE_CONTENT = f"""[Unit]
Description=Gunicorn instance to serve Central Auth Hub
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory={REMOTE_DIR}
Environment="PATH={REMOTE_DIR}/venv/bin"
ExecStart={REMOTE_DIR}/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8003 --timeout 3600

[Install]
WantedBy=multi-user.target
"""

def run_cmd(ssh, cmd):
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print(err)
    if exit_status != 0:
        raise Exception(f"Command failed: {cmd}")

def fix_deployment():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    sftp = ssh.open_sftp()

    print("Stopping service...")
    try:
        run_cmd(ssh, "systemctl stop apicentralizadora")
    except:
        pass

    print("Backing up .env and database specifically...")
    # The previous script might have put them in backend/ or root depending on state.
    # Let's try to find them.
    # We'll look in REMOTE_DIR and REMOTE_DIR/backend
    
    run_cmd(ssh, "rm -rf /tmp/fix_backup && mkdir -p /tmp/fix_backup")
    
    # Try backup from flat root
    run_cmd(ssh, f"cp {REMOTE_DIR}/.env /tmp/fix_backup/ 2>/dev/null || true")
    run_cmd(ssh, f"cp {REMOTE_DIR}/centralizador.db /tmp/fix_backup/ 2>/dev/null || true")
    
    # Try backup from backend/ subdir (if previous deployment existed)
    run_cmd(ssh, f"cp {REMOTE_DIR}/backend/.env /tmp/fix_backup/ 2>/dev/null || true")
    run_cmd(ssh, f"cp {REMOTE_DIR}/backend/centralizador.db /tmp/fix_backup/ 2>/dev/null || true")

    print("Re-cloning Repo (Flat structure)...")
    run_cmd(ssh, f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR}")
    run_cmd(ssh, f"git clone {REPO_URL} {REMOTE_DIR}")

    print("Restoring Config and DB...")
    run_cmd(ssh, f"cp /tmp/fix_backup/.env {REMOTE_DIR}/")
    run_cmd(ssh, f"cp /tmp/fix_backup/centralizador.db {REMOTE_DIR}/")

    print("Setting up Virtual Environment...")
    run_cmd(ssh, f"cd {REMOTE_DIR} && python3 -m venv venv")
    run_cmd(ssh, f"cd {REMOTE_DIR} && ./venv/bin/pip install --upgrade pip")
    run_cmd(ssh, f"cd {REMOTE_DIR} && ./venv/bin/pip install -r requirements.txt")

    print("Updating Systemd Service (Fixing Paths)...")
    with sftp.file("/etc/systemd/system/apicentralizadora.service", "w") as f:
        f.write(SERVICE_CONTENT)
    
    print("Reloading and Restarting Service...")
    run_cmd(ssh, "systemctl daemon-reload")
    run_cmd(ssh, "systemctl enable apicentralizadora")
    run_cmd(ssh, "systemctl restart apicentralizadora")

    print("Verifying Status...")
    run_cmd(ssh, "systemctl status apicentralizadora --no-pager")

    sftp.close()
    ssh.close()
    print("Fix Complete!")

if __name__ == "__main__":
    fix_deployment()
