import paramiko
import os

def fix_fono_gate():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("129.121.39.128", port=22022, username="root", password="Senhanova#123")
    
    # Read app.py
    stdin, stdout, stderr = ssh.exec_command("cat /opt/fonogramas-api/app.py")
    content = stdout.read().decode()
    
    # Remove the wrongly placed hook if it exists
    if "def check_sso():" in content:
        # We need a clean start. I'll find the part I added.
        import re
        content = re.sub(r'from flask import session\s+@app\.before_request.*?return redirect\(f"{HUB_WEB_URL}/login\?system_id={SYSTEM_ID}&redirect_url={return_url}"\)', '', content, flags=re.DOTALL)

    # Add imports at the top if missing
    if "from urllib.parse import quote" not in content:
        content = "from urllib.parse import quote\n" + content
    if "from flask import session" not in content:
        content = "from flask import session\n" + content

    # Add the hook at the END of initialization (before app.run)
    hook_code = """
@app.before_request
def check_sso():
    # Public paths
    if request.path.startswith('/auth/liberar') or \\
       request.path.startswith('/static') or \\
       request.path == '/health' or \\
       (request.blueprint == 'auth' and request.endpoint == 'auth.liberar'):
        return

    if not session.get('sso_verified'):
        HUB_WEB_URL = "https://hub-sbacem.vercel.app"
        SYSTEM_ID = 4
        return_url = quote(request.url)
        return redirect(f"{HUB_WEB_URL}/login?system_id={SYSTEM_ID}&redirect_url={return_url}")
"""
    
    insertion_point = "app.register_blueprint(api_bp)"
    if insertion_point in content:
        content = content.replace(insertion_point, insertion_point + hook_code)
    else:
        # Fallback to before create_all
        content = content.replace("with app.app_context():", hook_code + "\nwith app.app_context():")

    sftp = ssh.open_sftp()
    with sftp.file("/opt/fonogramas-api/app.py", "w") as f:
        f.write(content)
    sftp.close()
    
    print("Fonogramas app.py fixed.")
    ssh.exec_command("systemctl restart fonogramas")
    ssh.close()

if __name__ == "__main__":
    fix_fono_gate()
