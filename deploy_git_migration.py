import paramiko
import time

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"
REPO_URL = "https://github.com/gsPatrick/apicentralizadora.git"
REMOTE_DIR = "/opt/apicentralizadora"

SERVICE_CONTENT = f"""[Unit]
Description=Gunicorn instance to serve Central Auth Hub
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory={REMOTE_DIR}/backend
Environment="PATH={REMOTE_DIR}/backend/venv/bin"
ExecStart={REMOTE_DIR}/backend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8003 --timeout 3600

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

def migrate():
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

    print("Backing up .env, database, and venv...")
    # Current structure is flat.
    # We want to preserve .env and centralizador.db
    # We will backup to /tmp/backup_central
    run_cmd(ssh, "rm -rf /tmp/backup_central && mkdir -p /tmp/backup_central")
    # Backup .env
    try:
        run_cmd(ssh, f"cp {REMOTE_DIR}/.env /tmp/backup_central/")
    except:
        print("No .env found!")
    # Backup DB
    try:
        run_cmd(ssh, f"cp {REMOTE_DIR}/centralizador.db /tmp/backup_central/")
    except:
        print("No DB found!")

    print("Clearing directory and Cloning Repo...")
    # We verify we are in /opt/apicentralizadora before wiping
    run_cmd(ssh, f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR}")
    run_cmd(ssh, f"git clone {REPO_URL} {REMOTE_DIR}")

    print("Restoring backups to backend/...")
    # New structure has code in backend/
    run_cmd(ssh, f"cp /tmp/backup_central/.env {REMOTE_DIR}/backend/")
    run_cmd(ssh, f"cp /tmp/backup_central/centralizador.db {REMOTE_DIR}/backend/")

    print("Setting up Virtual Environment in backend/...")
    run_cmd(ssh, f"cd {REMOTE_DIR}/backend && python3 -m venv venv")
    run_cmd(ssh, f"cd {REMOTE_DIR}/backend && ./venv/bin/pip install --upgrade pip")
    # We need to ensure gunicorn and bcrypt are installed. requirements.txt in git should have them if I updated it locally.
    # I did update requirements.txt locally in Step 856.
    run_cmd(ssh, f"cd {REMOTE_DIR}/backend && ./venv/bin/pip install -r requirements.txt")

    print("Updating Systemd Service...")
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
    print("Migration Complete!")

if __name__ == "__main__":
    migrate()
