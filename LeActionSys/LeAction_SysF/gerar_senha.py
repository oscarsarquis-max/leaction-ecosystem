from werkzeug.security import generate_password_hash

# Defina a senha que você quer usar
minha_senha = "Cmgv6190!@#"

# Gera o hash seguro
hash_seguro = generate_password_hash(minha_senha)

print(f"\n--- COPIE O HASH ABAIXO ---")
print(hash_seguro)
print(f"---------------------------\n")