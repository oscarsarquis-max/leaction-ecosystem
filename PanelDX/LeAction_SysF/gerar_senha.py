"""Utilitário local: gera hash bcrypt para senhas de equipe (ctdi_team).

Uso:
  python gerar_senha.py "SuaSenhaSegura"
  # ou
  set ADMIN_PASSWORD=SuaSenhaSegura && python gerar_senha.py
"""
import os
import sys
from werkzeug.security import generate_password_hash

senha = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ADMIN_PASSWORD") or "").strip()

if not senha:
    print("Informe a senha como argumento ou via variável ADMIN_PASSWORD.", file=sys.stderr)
    sys.exit(1)

hash_seguro = generate_password_hash(senha)

print("\n--- COPIE O HASH ABAIXO ---")
print(hash_seguro)
print("---------------------------\n")
