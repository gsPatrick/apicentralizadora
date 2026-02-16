import os

def patch_fonogramas_auth(ssh):
    # Redirect /login to Central Hub
    hub_login_url = "https://hub-sbacem.vercel.app/login"
    
    # We want to replace the login function body to just redirect
    # We'll use a safer approach: append a redirect at the start of the login function
    
    commands = [
        f"sed -i 's/def login():/def login():\\n    return redirect(\"{hub_login_url}\")/' /opt/fonogramas-api/auth/routes.py"
    ]
    
    for cmd in commands:
        ssh.exec_command(cmd)

if __name__ == "__main__":
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("129.121.39.128", port=22022, username="root", password="Senhanova#123")
    patch_fonogramas_auth(ssh)
    ssh.close()
    print("Fonogramas auth patched.")
