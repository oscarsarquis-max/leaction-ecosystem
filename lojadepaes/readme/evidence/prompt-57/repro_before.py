import json
import time
import urllib.request

BASE = "https://lojadepaes.com.br"
QUESTION = "Quero comprar um pão rústico de fermentação natural. Com o que combina na hora de servir?"


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


def main() -> None:
    status, first_ms, first = post([{"role": "user", "content": QUESTION}])
    report = {
        "version_probe": "prod-before-57",
        "first": {
            "http": status,
            "ms": int(first_ms),
            "unavailable": first.get("unavailable"),
            "reply": first.get("reply"),
            "links": first.get("links") or [],
            "is_false_length": "longa demais" in (first.get("reply") or ""),
        },
    }
    history = [
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": first.get("reply") or ""},
        {"role": "user", "content": "E uma opção sem queijo?"},
    ]
    status2, second_ms, second = post(history)
    report["second"] = {
        "http": status2,
        "ms": int(second_ms),
        "unavailable": second.get("unavailable"),
        "reply": second.get("reply"),
        "links": second.get("links") or [],
        "is_false_length": "longa demais" in (second.get("reply") or ""),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
