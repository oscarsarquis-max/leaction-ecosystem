import subprocess

text = subprocess.check_output(["sudo", "nginx", "-T"], stderr=subprocess.DEVNULL, text=True, errors="replace")
current_server = []
for line in text.splitlines():
    stripped = line.strip()
    if stripped.startswith("server {"):
        current_server = [stripped]
        continue
    if current_server is not None:
        current_server.append(stripped)
        if stripped == "}":
            block = "\n".join(current_server)
            if "actionhub.com.br" in block or "4001" in block:
                names = [row for row in current_server if row.startswith("server_name") or row.startswith("listen") or row.startswith("location")]
                print("---")
                for row in names:
                    print(row)
            current_server = None
