"""Confere canal e os três registros deixados para revisão. Não imprime contato."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.managerial_exclusion import active_exclusion_sets
from app.models.date_requests import DateRequest
from app.models.managerial import OpsChannelSetting, OpsOwnerAlert
from app.models.orders import Order

LEFT = ("LP87D4BCF4E1", "LP23FF6F00E2")
LEFT_DATE = "SD51A91EFF"


def main() -> None:
    settings = get_settings()
    mail = (settings.mail_ops_to or "").strip().lower()
    print("mail_match", mail == "oscar@oscarsarquis.com.br")
    print("mail_set", bool(mail))
    print("wa_enabled", bool(settings.whatsapp_ops_enabled))
    print("wa_provider_set", bool((settings.whatsapp_provider or "").strip()))
    print("wa_to_set", bool((settings.whatsapp_ops_to or "").strip()))
    session = Session(get_engine())
    try:
        excluded_orders, excluded_dates = active_exclusion_sets(session)
        for reference in LEFT:
            order = session.scalar(select(Order).where(Order.public_reference == reference))
            print(
                "left",
                reference,
                order.status if order else "missing",
                "holds" if order and order.holds_capacity else "no_hold",
                "excluded" if order and order.id in excluded_orders else "visible",
            )
        from app.domain.attendance import date_request_reference

        found = None
        for row in session.scalars(select(DateRequest)):
            if date_request_reference(row.id) == LEFT_DATE:
                found = row
                break
        if found is None:
            print("left", LEFT_DATE, "missing")
        else:
            print(
                "left",
                LEFT_DATE,
                found.status,
                "excluded" if found.id in excluded_dates else "visible",
            )
        print("owner_alerts", session.scalar(select(func.count()).select_from(OpsOwnerAlert)) or 0)
        row = session.get(OpsChannelSetting, "whatsapp")
        print("wa_row", "absent" if row is None else "present")
        print("wa_row_enabled", False if row is None else bool(row.enabled))
    finally:
        session.close()


if __name__ == "__main__":
    main()
