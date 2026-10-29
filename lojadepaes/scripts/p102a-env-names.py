"""Lista só nomes de variáveis de canal. Não imprime valores."""

import os

NEEDLES = (
    "WHATS",
    "WABA",
    "TWILIO",
    "GRAPH",
    "ZAPI",
    "EVOLUTION",
    "GUPSHUP",
    "MESSAGEBIRD",
    "DIALOG",
    "META_",
    "SES",
    "SMTP",
    "MAIL",
)


def main() -> None:
    names = sorted(
        key
        for key in os.environ
        if any(needle in key.upper() for needle in NEEDLES)
    )
    print("channel_env_names")
    for name in names:
        print(name)
    if not names:
        print("none")


if __name__ == "__main__":
    main()
