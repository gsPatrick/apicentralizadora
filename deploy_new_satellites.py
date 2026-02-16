import paramiko
import os
import time

# Configuration
HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

# Repositories
REPOS = {
    "fonogramas": {
        "url": "https://github.com/gsPatrick/fonogramas-api.git",
        "dir": "/opt/fonogramas-api",
        "domain": "fonogramas.sbacem.app.br", # Corrected domain
        "port": 8004,
        "type": "flask"
    },
    "cadastro": {
        "url": "https://github.com/gsPatrick/cadastro-api.git",
        "dir": "/opt/cadastro-api",
        "api_domain": "api.amplo.app.br",
        "web_domain": "amplo.app.br",
        "api_port": 8005,
        "web_port": 3000,
        "type": "monorepo"
    }
}

HUB_URL = "https://api.sbacem.com.br/apicentralizadora"
HUB_WEB_URL = "https://hub-sbacem.vercel.app"

def execute_commands(ssh, commands, cwd=None):
    for cmd in commands:
        full_cmd = f"cd {cwd} && {cmd}" if cwd else cmd
        print(f"Executing: {full_cmd}")
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(f"STDOUT: {out}")
        if err: print(f"STDERR: {err}")
        if exit_status != 0:
            print(f"Command failed with status {exit_status}")
            return False
    return True

def deploy_fonogramas(ssh, sftp):
    repo = REPOS["fonogramas"]
    print(f"\n--- Deploying {repo['domain']} ---")
    
    # Clone or Pull
    ssh.exec_command(f"rm -rf {repo['dir']}")
    time.sleep(1)
    ssh.exec_command(f"git clone {repo['url']} {repo['dir']}")
    time.sleep(1)
    
    # Patch Auth to redirect to Hub
    patch_cmd = f"sed -i 's/def login():/def login():\\n    return redirect(\"{HUB_WEB_URL}/login\")/' {repo['dir']}/auth/routes.py"
    ssh.exec_command(patch_cmd)

    # Setup Venv
    execute_commands(ssh, [
        "python3 -m venv venv",
        "./venv/bin/pip install --upgrade pip",
        "./venv/bin/pip install -r requirements.txt gunicorn requests"
    ], cwd=repo['dir'])
    
    # .env
    env_content = f"""SECRET_KEY=fonogramas_secret_key_992
FLASK_APP=app.py
FLASK_ENV=production
HUB_URL={HUB_URL}
CORS_ORIGINS=*
"""
    with sftp.file(f"{repo['dir']}/.env", "w") as f:
        f.write(env_content)
        
    # Systemd Service
    service_content = f"""[Unit]
Description=Gunicorn instance to serve Fonogramas
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory={repo['dir']}
Environment="PATH={repo['dir']}/venv/bin"
EnvironmentFile={repo['dir']}/.env
ExecStart={repo['dir']}/venv/bin/gunicorn -w 4 -b 127.0.0.1:{repo['port']} app:app --timeout 300

[Install]
WantedBy=multi-user.target
"""
    with sftp.file(f"/etc/systemd/system/fonogramas.service", "w") as f:
        f.write(service_content)
    
    execute_commands(ssh, ["systemctl daemon-reload", "systemctl enable fonogramas", "systemctl restart fonogramas"])

def deploy_cadastro(ssh, sftp):
    repo = REPOS["cadastro"]
    print(f"\n--- Deploying {repo['web_domain']} and {repo['api_domain']} ---")
    
    # Clone
    ssh.exec_command(f"rm -rf {repo['dir']}")
    time.sleep(1)
    ssh.exec_command(f"git clone {repo['url']} {repo['dir']}")
    time.sleep(1)

    # Monorepo setup
    api_dir = f"{repo['dir']}/apps/api"
    web_dir = f"{repo['dir']}/apps/web"
    
    # API .env
    api_env_content = f"""DATABASE_URL="postgresql://sistemacadastro:123456@localhost:5432/sistemacadastro"
JWT_ACCESS_SECRET="cadastro_access_secret_992"
JWT_REFRESH_SECRET="cadastro_refresh_secret_992"
JWT_SECRET="cadastro_secret_key"
DATA_ENCRYPTION_KEY="H6ivbNd/39e3hPLGq+clsQlxcF5KLUgRsCKVwnzgQUY="
CLICKSIGN_ACCESS_TOKEN="dummy_clicksign_token"
PORT={repo['api_port']}
HUB_URL={HUB_URL}
REDIS_HOST=localhost
REDIS_PORT=6379
"""
    ssh.exec_command(f"mkdir -p {api_dir}")
    with sftp.file(f"{api_dir}/.env", "w") as f:
        f.write(api_env_content)

    # Web .env
    web_env_content = f"""NEXT_PUBLIC_API_BASE_URL=https://{repo['api_domain']}
NEXT_PUBLIC_HUB_URL={HUB_WEB_URL}
"""
    ssh.exec_command(f"mkdir -p {web_dir}")
    with sftp.file(f"{web_dir}/.env", "w") as f:
        f.write(web_env_content)

    # Install & Build
    execute_commands(ssh, [
        "npm install -g pnpm",
        "pnpm install --shamefully-hoist",
        "npx prisma generate" # Inside root or filter? Filter is safer.
    ], cwd=repo['dir'])

    execute_commands(ssh, ["npx prisma generate"], cwd=api_dir)

    execute_commands(ssh, [
        "pnpm --filter @sistemacadastro/shared build",
        "pnpm --filter api build",
        "pnpm --filter web build"
    ], cwd=repo['dir'])
    
    execute_commands(ssh, ["npx prisma migrate deploy"], cwd=api_dir)
    
    # PM2
    execute_commands(ssh, [
        f"pm2 delete cadastro-api || true",
        f"pm2 delete cadastro-web || true",
        f"pm2 start dist/src/main.js --name cadastro-api --env PORT={repo['api_port']}",
    ], cwd=api_dir)
    
    execute_commands(ssh, [
         f"pm2 start npm --name cadastro-web -- start -- -p {repo['web_port']}"
    ], cwd=web_dir)

def setup_nginx(ssh, sftp):
    # Map correct domains to new services
    # Fonogramas
    fono = REPOS["fonogramas"]
    fono_conf = f"""server {{
    listen 80;
    server_name {fono['domain']};
    location / {{
        proxy_pass http://127.0.0.1:{fono['port']};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    with sftp.file("/etc/nginx/sites-available/fonogramas_new", "w") as f:
        f.write(fono_conf)
    
    # Cadastro
    cad = REPOS["cadastro"]
    cad_conf = f"""server {{
    listen 80;
    server_name {cad['web_domain']};
    location / {{
        proxy_pass http://127.0.0.1:{cad['web_port']};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
server {{
    listen 80;
    server_name {cad['api_domain']};
    location / {{
        proxy_pass http://127.0.0.1:{cad['api_port']};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
    with sftp.file("/etc/nginx/sites-available/cadastro_new", "w") as f:
        f.write(cad_conf)

    # Enable and test
    ssh.exec_command("rm -f /etc/nginx/sites-enabled/fonogramas")
    ssh.exec_command("rm -f /etc/nginx/sites-enabled/sistemacadastro")
    ssh.exec_command("ln -s /etc/nginx/sites-available/fonogramas_new /etc/nginx/sites-enabled/fonogramas")
    ssh.exec_command("ln -s /etc/nginx/sites-available/cadastro_new /etc/nginx/sites-enabled/sistemacadastro")
    
    execute_commands(ssh, ["nginx -t", "systemctl reload nginx"])

def run_deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    sftp = ssh.open_sftp()
    
    deploy_fonogramas(ssh, sftp)
    deploy_cadastro(ssh, sftp)
    setup_nginx(ssh, sftp)
    
    sftp.close()
    ssh.close()
    print("\nDeployment finished!")

if __name__ == "__main__":
    run_deploy()
