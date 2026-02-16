import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

def migrate():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("Pulling latest changes...")
    ssh.exec_command("cd /opt/apicentralizadora && git pull")
    
    print("Migrating Database (Adding is_active column)...")
    # Using python to run a raw SQL command via sqlalchemy or just raw psql if available, but simplest is probably a small python script on the remote.
    # Actually, I'll just write a migration script here and push it, then run it remotely.
    
    migration_script = """
from app.config.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
        conn.commit()
        print("Migration successful: Added is_active column.")
    except Exception as e:
        print(f"Migration failed (maybe column exists): {e}")
"""
    
    # Write the migration script to a temp file on remote
    sftp = ssh.open_sftp()
    with sftp.file("/opt/apicentralizadora/migrate_users.py", "w") as f:
        f.write(migration_script)
        
    # Execute it
    stdin, stdout, stderr = ssh.exec_command("cd /opt/apicentralizadora && ./venv/bin/python3 migrate_users.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print("Restarting Service...")
    ssh.exec_command("systemctl restart apicentralizadora")
    
    ssh.close()

if __name__ == "__main__":
    migrate()
