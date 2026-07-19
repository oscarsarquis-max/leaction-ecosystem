"""Utilitários compartilhados para spawn/controle de workers em dev local."""
import os
import subprocess
import sys

from ai_engine.worker_lock import MASTER_WORKER_PORT, MODULADOR_WORKER_PORT

_bg_worker_procs = []


def _free_local_port(port):
    """Libera porta local matando o processo listener (dev Windows/Linux)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                if f":{port}" not in line or "LISTENING" not in line.upper():
                    continue
                pid = line.split()[-1]
                if pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True,
                        check=False,
                    )
        else:
            subprocess.run(
                ["fuser", "-k", f"{port}/tcp"],
                capture_output=True,
                check=False,
            )
    except Exception:
        pass


def terminate_background_workers():
    """Encerra workers filhos antes de um novo spawn (reload do Flask debug)."""
    global _bg_worker_procs
    for proc in _bg_worker_procs:
        if proc.poll() is not None:
            continue
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    _bg_worker_procs = []


def _kill_stale_paneldx_workers():
    """Encerra workers órfãos de reloads anteriores do Flask (sem lock de porta)."""
    markers = ("ai_engine\\worker.py", "ai_engine/worker.py", "modulador_worker.py")
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["wmic", "process", "get", "ProcessId,CommandLine"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            my_pid = str(os.getpid())
            for line in out.splitlines():
                if not any(m in line for m in markers):
                    continue
                pid = line.strip().split()[-1]
                if pid.isdigit() and pid != my_pid:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=False)
        else:
            subprocess.run(["pkill", "-f", "ai_engine/worker.py"], check=False)
            subprocess.run(["pkill", "-f", "modulador_worker.py"], check=False)
    except Exception:
        pass


def spawn_background_workers(base_path):
    """Inicia worker Master e Modulador, substituindo instâncias anteriores."""
    global _bg_worker_procs
    terminate_background_workers()
    _kill_stale_paneldx_workers()
    _free_local_port(MASTER_WORKER_PORT)
    _free_local_port(MODULADOR_WORKER_PORT)

    env = os.environ.copy()
    env["PANELDX_WORKER_SPAWNED_BY"] = "flask"

    worker_path = os.path.join(base_path, "ai_engine", "worker.py")
    modulador_path = os.path.join(base_path, "ai_engine", "modulador_worker.py")

    _bg_worker_procs.append(
        subprocess.Popen([sys.executable, worker_path], env=env)
    )
    print("🛰️  [SISTEMA] Worker IA Master despertado.", file=sys.stderr)

    _bg_worker_procs.append(
        subprocess.Popen([sys.executable, modulador_path], env=env)
    )
    print("🤖 [SISTEMA] Worker Agente Modulador despertado com sucesso.", file=sys.stderr)
