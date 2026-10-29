from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine, reset_engine
from app.models.gigio import GigioPairingReference

reset_engine()
with Session(get_engine()) as session:
    rows = list(session.scalars(select(GigioPairingReference).order_by(GigioPairingReference.profile_key)))
print("count", len(rows))
for row in rows:
    print(
        row.profile_key,
        row.editorial_status,
        row.retrieval_role,
        row.verification_status,
        row.reviewed_by or "-",
        "loja_choice",
        row.loja_choice,
        "v" + str(row.version),
    )
    print(" ", row.source_url)
published = [row.profile_key for row in rows if row.editorial_status == "published"]
print("published", ",".join(published))
if set(published) != {"wine-churrasco-porco", "wine-queijo-tabua"}:
    raise SystemExit("published set diverges from authorized pilot")
if any(row.loja_choice for row in rows):
    raise SystemExit("loja_choice must stay false")
