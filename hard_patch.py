import paramiko
import io

def hard_patch():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("129.121.39.128", port=22022, username="root", password="Senhanova#123")
    
    # Patch Fonogramas auth/routes.py
    # We will read the whole file, replace the login function, and write it back.
    stdin, stdout, stderr = ssh.exec_command("cat /opt/fonogramas-api/auth/routes.py")
    content = stdout.read().decode()
    
    if "return redirect(\"https://hub-sbacem.vercel.app/login\")" not in content:
        # Replacement with a simpler redirect
        old_login = """@auth_bp.route('/login', methods=['GET', 'POST'])
def login():"""
        new_login = """@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    return redirect("https://hub-sbacem.vercel.app/login")"""
        
        patched_content = content.replace(old_login, new_login)
        
        sftp = ssh.open_sftp()
        with sftp.file("/opt/fonogramas-api/auth/routes.py", "w") as f:
            f.write(patched_content)
        sftp.close()
        print("Fonogramas auth patched successfully.")
    else:
        print("Fonogramas auth already patched.")

    ssh.exec_command("systemctl restart fonogramas")
    ssh.close()

if __name__ == "__main__":
    hard_patch()
