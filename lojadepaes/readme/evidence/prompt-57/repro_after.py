import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://lojadepaes.com.br"
QUESTION = "Quero comprar um pão rústico de fermentação natural. Com o que combina na hora de servir?"
FOLLOW_NO_CHEESE = "E uma opção sem queijo?"
FERMENT_VS_KNEAD = "Qual a diferença entre fermentação natural e pão sovado?"
PUBLISHED_RECIPE = "Tem uma receita publicada para esse pão?"
OUT = Path(__file__).with_name("repro_after.json")


def get(path: str) -> tuple[int, str]:
    req = urllib.request.Request(BASE + path, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def post(messages: list[dict]) -> tuple[int, float, dict]:
    body = json.dumps(
        {"messages": messages, "page": {"path": "/"}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/v1/gigio/chat",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        return resp.status, (time.perf_counter() - started) * 1000, payload


def summarize(status: int, ms: float, payload: dict) -> dict:
    reply = payload.get("reply") or ""
    return {
        "http": status,
        "ms": int(ms),
        "unavailable": payload.get("unavailable"),
        "reply": reply,
        "links": payload.get("links") or [],
        "is_false_length": "longa demais" in reply,
        "is_incomplete": "Não consegui concluir a resposta agora" in reply,
    }


def main() -> None:
    html_status, html = get("/")
    bundle = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
    health_status, health = get("/api/v1/health")
    ready_status, ready = get("/api/v1/ready")
    gigio_status, gigio = get("/api/v1/gigio/status")
    report: dict = {
        "version_probe": {
            "html_http": html_status,
            "bundle": bundle.group(0) if bundle else None,
            "health_http": health_status,
            "health": json.loads(health),
            "ready_http": ready_status,
            "ready": json.loads(ready),
            "gigio_http": gigio_status,
            "gigio": json.loads(gigio),
        }
    }

    status, first_ms, first = post([{"role": "user", "content": QUESTION}])
    report["first"] = summarize(status, first_ms, first)
    history = [
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": first.get("reply") or ""},
        {"role": "user", "content": FOLLOW_NO_CHEESE},
    ]
    status2, second_ms, second = post(history)
    report["second"] = summarize(status2, second_ms, second)
    history.extend(
        [
            {"role": "assistant", "content": second.get("reply") or ""},
            {"role": "user", "content": FERMENT_VS_KNEAD},
        ]
    )
    status3, third_ms, third = post(history)
    report["third"] = summarize(status3, third_ms, third)
    history.extend(
        [
            {"role": "assistant", "content": third.get("reply") or ""},
            {"role": "user", "content": PUBLISHED_RECIPE},
        ]
    )
    status4, fourth_ms, fourth = post(history)
    report["fourth"] = summarize(status4, fourth_ms, fourth)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
