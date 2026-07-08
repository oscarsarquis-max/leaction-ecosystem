"""Lock de instância única para workers locais (evita processos zumbis após reload do Flask)."""
import socket
import sys

# Portas locais reservadas — apenas bind em 127.0.0.1
MASTER_WORKER_PORT = 51999
MODULADOR_WORKER_PORT = 51998


def acquire_worker_lock(worker_name, port):
    """
    Garante uma única instância do worker por porta.
    Mantém o socket aberto durante toda a vida do processo.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
    except OSError:
        print(
            f"⚠️ [{worker_name}] Outra instância já está ativa na porta {port}. "
            f"Encerrando processo duplicado.",
            flush=True,
        )
        sys.exit(0)
    return sock
