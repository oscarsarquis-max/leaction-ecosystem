from app.core.config import get_settings
from app.domain.gigio.rules import PROCESS_RULES_VERSION

s = get_settings()
print("pairing", s.gigio_pairing_refs_enabled)
print("gigio", s.gigio_enabled)
print("gigio_acc", s.gigio_accompaniments_enabled)
print("public_acc", s.public_accompaniments_enabled)
print("rules", PROCESS_RULES_VERSION)
