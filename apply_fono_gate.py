import paramiko
import os

def apply_sso_gate():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("129.121.39.128", port=22022, username="root", password="Senhanova#123")
    
    # 1. Update auth/routes.py: Revert login hard redirect and add /liberar
    stdin, stdout, stderr = ssh.exec_command("cat /opt/fonogramas-api/auth/routes.py")
    routes_content = stdout.read().decode()
    
    # Revert hard redirect if present
    bad_line = '    return redirect("https://hub-sbacem.vercel.app/login")'
    if bad_line in routes_content:
        routes_content = routes_content.replace(bad_line, "")
    
    # Add liberar route (if missing)
    if "@auth_bp.route('/liberar')" not in routes_content:
        liberar_code = """
@auth_bp.route('/liberar')
def liberar():
    from flask import session, current_app
    import requests
    ticket = request.args.get('ticket')
    if not ticket:
        return "Ticket missing", 400
    
    hub_url = os.environ.get('HUB_URL', 'https://api.sbacem.com.br/apicentralizadora')
    system_id = 4 # Fonogramas
    
    try:
        res = requests.post(f"{hub_url}/auth/validate-ticket", json={
            "ticket": ticket,
            "system_id": system_id
        })
        if res.status_code == 200:
            session['sso_verified'] = True
            session.permanent = True
            return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"SSO Error: {e}")
    
    return "SSO Verification Failed", 401
"""
        routes_content += liberar_code
        
        sftp = ssh.open_sftp()
        with sftp.file("/opt/fonogramas-api/auth/routes.py", "w") as f:
            f.write(routes_content)
        sftp.close()
        print("Fonogramas routes updated.")

    # 2. Update app.py: Add before_request hook
    stdin, stdout, stderr = ssh.exec_command("cat /opt/fonogramas-api/app.py")
    app_content = stdout.read().decode()
    
    if "def check_sso():" not in app_content:
        # We need to insert it after app initialization but before blueprints
        hook_code = """
from flask import session

@app.before_request
def check_sso():
    # Public paths and static files
    if request.path.startswith('/auth/liberar') or \\
       request.path.startswith('/static') or \\
       request.path == '/health' or \\
       (request.blueprint == 'auth' and request.endpoint == 'auth.liberar'):
        return

    if not session.get('sso_verified'):
        HUB_WEB_URL = "https://hub-sbacem.vercel.app"
        SYSTEM_ID = 4
        # Use returnUrl to come back after login
        from urllib.parse import quote
        return_url = quote(request.url)
        return redirect(f"{HUB_WEB_URL}/login?system_id={SYSTEM_ID}&redirect_url={return_url}")
"""
        # Insert after "app = Flask(__name__)"
        insertion_point = "app = Flask(__name__)"
        app_content = app_content.replace(insertion_point, insertion_point + hook_code)
        
        sftp = ssh.open_sftp()
        with sftp.file("/opt/fonogramas-api/app.py", "w") as f:
            f.write(app_content)
        sftp.close()
        print("Fonogramas app.py updated with SSO gate.")

    ssh.exec_command("systemctl restart fonogramas")
    ssh.close()

if __name__ == "__main__":
    apply_sso_gate()
