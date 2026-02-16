import paramiko

HOST = "129.121.39.128"
PORT = 22022
USER = "root"
PASSWORD = "Senhanova#123"

NGINX_CONTENT = """    location /apicentralizadora/ {
        proxy_pass http://127.0.0.1:8003/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cookie path rewriting
        proxy_cookie_path / /apicentralizadora/;
    }
"""

def fix():
    print(f"Connecting to {HOST}:{PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    sftp = ssh.open_sftp()
    SITE_FILE = "/etc/nginx/sites-available/sbacem-api"
    
    with sftp.file(SITE_FILE, "r") as f:
        content = f.read().decode()

    # 1. Remove the bad block
    # It was appended loosely at the end or in the second block. 
    # Let's simple remove the string "location /apicentralizadora/ {" and everything until "}"
    # But doing it robustly:
    
    # Check if correct block exists (in first server block). 
    # First server block ends at first "}". 
    # Find first "}".
    first_brace_index = content.find("}")
    # But wait, nested braces in location blocks!
    # "location / { ... }" has a closing brace.
    # "server { ... location / { ... } ... }"
    
    # Simple logic: split by "server {". 
    # 0: empty or comments
    # 1: First server block (HTTPS)
    # 2: Second server block (HTTP)
    
    parts = content.split("server {")
    if len(parts) < 3:
        print("Could not parse structure (less than 2 server blocks).")
        return

    # parts[1] is the body of the first server block (without "server {" prefix).
    # parts[2] is the body of the second server block.
    
    # Clean up the bad insertion from parts[2] or wherever it is.
    # The bad insertion likely spans or is at the end of the file.
    # Let's remove any existing /apicentralizadora/ block from the WHOLE content first to start clean.
    
    lines = content.splitlines()
    clean_lines = []
    skip = False
    for line in lines:
        if "location /apicentralizadora/ {" in line:
            skip = True
        if skip and line.strip() == "}":
            skip = False
            continue
        if not skip:
            clean_lines.append(line)
            
    content = "\n".join(clean_lines)
    
    # Now insert into the FIRST server block.
    # We need to find the closing brace of the first server block.
    # We can iterate through lines, counting braces.
    
    brace_count = 0
    insert_index = -1
    server_block_count = 0
    
    lines = content.splitlines()
    final_lines = []
    
    inserted = False
    
    for i, line in enumerate(lines):
        final_lines.append(line)
        
        if "server {" in line:
            server_block_count += 1
            brace_count += 1
        else:
            brace_count += line.count("{") - line.count("}")
        
        # If we are in the first server block (server_block_count == 1) 
        # and brace_count drops to 0 (closing the server block)
        # We should insert BEFORE this line (which is "}")
        if server_block_count == 1 and brace_count == 0 and not inserted:
            # We just added the "}" to final_lines.
            # Pop it, insert block, then add "}" back.
            last_line = final_lines.pop() # This is "}"
            final_lines.append(NGINX_CONTENT)
            final_lines.append(last_line)
            inserted = True
            
    new_content = "\n".join(final_lines)
    
    print("Writing fixed content...")
    with sftp.file(SITE_FILE, "w") as f:
        f.write(new_content)
        
    print("Reloading Nginx...")
    ssh.exec_command("nginx -t && systemctl reload nginx")
    
    sftp.close()
    ssh.close()
    print("Fixed!")

if __name__ == "__main__":
    fix()
