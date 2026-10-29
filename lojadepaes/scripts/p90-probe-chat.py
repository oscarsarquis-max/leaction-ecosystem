import json
import urllib.request

ORIGIN = "https://lojadepaes.com.br"
status = json.loads(urllib.request.urlopen(f"{ORIGIN}/api/v1/gigio/status", timeout=20).read())


def chat(messages):
    req = urllib.request.Request(
        f"{ORIGIN}/api/v1/gigio/chat",
        data=json.dumps({"messages": messages, "page": {"path": "/"}}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


ham = "queremos fazer um hambúrguer bem legal, com batatas e molho. que sugestão de acompanhamento você poderia me dar?"
first = chat([{"role": "user", "content": ham}])
second = chat(
    [
        {"role": "user", "content": ham},
        {"role": "assistant", "content": first.get("reply") or ""},
        {"role": "user", "content": "Onde compro um Fusca?"},
    ]
)
thanks = chat(
    [
        {"role": "user", "content": ham},
        {"role": "assistant", "content": first.get("reply") or ""},
        {"role": "user", "content": "Obrigado!"},
    ]
)
print(
    json.dumps(
        {
            "rules": status.get("rules_version"),
            "first_cta": (first.get("cta") or {}).get("label"),
            "first_href": (first.get("cta") or {}).get("href"),
            "fusca_cta": second.get("cta"),
            "fusca_builder": second.get("builder_cta"),
            "fusca_reply": str(second.get("reply") or "")[:280],
            "thanks_cta": thanks.get("cta"),
        },
        ensure_ascii=False,
        indent=2,
    )
)
