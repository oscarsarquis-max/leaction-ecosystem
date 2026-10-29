import json, pathlib, os, subprocess, sys
landing = pathlib.Path("/tmp/restore-landing.json").read_text(encoding="utf-8")
instr = pathlib.Path("/tmp/restore-instr.txt").read_text(encoding="utf-8")
# discover creds from env
user = os.environ.get("POSTGRES_USER") or os.environ.get("POSTGRES_USER".lower()) or "admin"
password = os.environ.get("POSTGRES_PASSWORD") or "password123"
db = os.environ.get("POSTGRES_DB") or "leaction_hub"
env = os.environ.copy()
env["PGPASSWORD"] = password
sql = "INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data, updated_at) VALUES ('panne-demo', %s::jsonb, %s, CURRENT_TIMESTAMP) ON CONFLICT (config_key) DO UPDATE SET landing_page_data = EXCLUDED.landing_page_data, instructions_data = EXCLUDED.instructions_data, updated_at = CURRENT_TIMESTAMP;"
# use psql with dollar quoting via temp files
pathlib.Path("/tmp/landing.sql.json").write_text(landing, encoding="utf-8")
pathlib.Path("/tmp/instr.sql.txt").write_text(instr, encoding="utf-8")
psql = [
  "psql", "-U", user, "-d", db, "-v", "ON_ERROR_STOP=1",
  "-c", "UPDATE cms_site_config SET landing_page_data = (pg_read_file('/tmp/restore-landing.json'))::jsonb, instructions_data = pg_read_file('/tmp/restore-instr.txt'), updated_at = CURRENT_TIMESTAMP WHERE config_key = 'panne-demo';"
]
# pg_read_file limited — use COPY FROM PROGRAM or stdin
proc = subprocess.run(
  ["psql", "-U", user, "-d", db, "-tAc", "SELECT landing_page_data->'columns'->0->>'title' FROM cms_site_config WHERE config_key='panne-demo';"],
  env=env, capture_output=True, text=True
)
print("BEFORE", proc.stdout.strip(), proc.stderr.strip())
# Write SQL with properly escaped dollar quote
sql_path = pathlib.Path("/tmp/restore.sql")
sql_path.write_text(
  "UPDATE cms_site_config SET landing_page_data = $json$" + landing + "$json$::jsonb, instructions_data = $txt$" + instr + "$txt$, updated_at = CURRENT_TIMESTAMP WHERE config_key = 'panne-demo';\n",
  encoding="utf-8",
)
proc2 = subprocess.run(["psql", "-U", user, "-d", db, "-v", "ON_ERROR_STOP=1", "-f", "/tmp/restore.sql"], env=env, capture_output=True, text=True)
print("PSQL", proc2.returncode, proc2.stdout, proc2.stderr)
proc3 = subprocess.run(
  ["psql", "-U", user, "-d", db, "-tAc", "SELECT landing_page_data->'columns'->0->>'title' FROM cms_site_config WHERE config_key='panne-demo';"],
  env=env, capture_output=True, text=True
)
print("AFTER", proc3.stdout.strip())
if "SYNTH" in proc3.stdout:
  sys.exit(2)
print("RESTORE_OK")
