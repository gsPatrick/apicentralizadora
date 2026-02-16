import paramiko
import os
import time

# Configuration
HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"
REMOTE_DIR = "/opt/apicentralizadora"
LOCAL_ARCHIVE = "backend.tar.gz"

# Env Content for Production
ENV_CONTENT = """PROJECT_NAME="Central Auth Hub"
DATABASE_URL=sqlite:///./centralizador.db
SECRET_KEY=prod_secret_key_bf3c8592_change_me_to_something_very_secure_in_real_prod
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
TRANSFER_TOKEN_EXPIRE_SECONDS=60
SERVER_NAME=api.sbacem.com.br
ROOT_PATH=/apicentralizadora
COOKIE_DOMAIN=.sbacem.com.br
"""

# Systemd Service Content
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

# Nginx Config Content
NGINX_CONTENT = """location /apicentralizadora/ {
    proxy_pass http://127.0.0.1:8003/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Cookie path rewriting
    proxy_cookie_path / /apicentralizadora/;
}
"""

def deploy():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    sftp = ssh.open_sftp()

    print("Creating remote directory...")
    ssh.exec_command(f"mkdir -p {REMOTE_DIR}")

    print(f"Uploading {LOCAL_ARCHIVE}...")
    sftp.put(LOCAL_ARCHIVE, f"{REMOTE_DIR}/{LOCAL_ARCHIVE}")

    print("Extracting archive...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && tar -xzf {LOCAL_ARCHIVE} && rm {LOCAL_ARCHIVE}")
    print(stdout.read().decode())
    print(stderr.read().decode())

    print("Writing .env file...")
    with sftp.file(f"{REMOTE_DIR}/.env", "w") as f:
        f.write(ENV_CONTENT)

    print("Setting up Virtual Environment (this may take a minute)...")
    # Using specific python3 command or ensuring it exists
    cmds = [
        f"cd {REMOTE_DIR}",
        "python3 -m venv venv",
        "./venv/bin/pip install --upgrade pip",
        "./venv/bin/pip install -r requirements.txt"
    ]
    
    for cmd in cmds:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && {cmd}")
        out = stdout.read().decode()
        err = stderr.read().decode()
        if err and "warning" not in err.lower(): 
            print(f"STDERR: {err}")
        if out:
             print(f"STDOUT: {out}")

    print("Configuring Systemd Service...")
    with sftp.file("/etc/systemd/system/apicentralizadora.service", "w") as f:
        f.write(SERVICE_CONTENT)
    
    print("Reloading Systemd and Restarting Service...")
    ssh.exec_command("systemctl daemon-reload")
    ssh.exec_command("systemctl enable apicentralizadora")
    ssh.exec_command("systemctl restart apicentralizadora")

    print("Configuring Nginx...")
    # Check if site file exists, if so append or check if location already there. 
    # For now, assuming we append or create a snippet. User said "Add to ... /etc/nginx/sites-available/sbacem-api"
    # We will try to read it first? Or just append?
    # Safer to write a separate config file if included? 
    # User said: "Adicione ao arquivo /etc/nginx/sites-available/sbacem-api".
    # I'll try to read it, check if block exists, if not append.
    
    SITE_FILE = "/etc/nginx/sites-available/sbacem-api"
    try:
        with sftp.file(SITE_FILE, "r") as f:
            current_conf = f.read().decode()
    except IOError:
        print("Nginx site file not found, creating new one (WARNING: Verify this)...")
        current_conf = "server {\n    listen 80;\n    server_name api.sbacem.com.br;\n"

    if "location /apicentralizadora/" not in current_conf:
        print("Appending Nginx location block...")
        # Assuming the file ends with '}', we need to insert before the last brace or just append if it's partial.
        # Simple append for now if format allows, but valid nginx conf usually ends with }.
        # Let's try to assume standard structure.
        if current_conf.strip().endswith("}"):
            new_conf = current_conf.rstrip()[:-1] + "\n" + NGINX_CONTENT + "\n}"
        else:
            new_conf = current_conf + "\n" + NGINX_CONTENT
        
        with sftp.file(SITE_FILE, "w") as f:
            f.write(new_conf)
            
        print("Reloading Nginx...")
        ssh.exec_command("nginx -t && systemctl reload nginx")
    else:
        print("Nginx location already exists. Skipping.")

    print("Seeding Database...")
    # Run seed script
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && ./venv/bin/python seed_db.py")
    print(stdout.read().decode())
    print(stderr.read().decode())

    sftp.close()
    ssh.close()
    print("Deployment Configured Successfully!")

if __name__ == "__main__":
    deploy()
