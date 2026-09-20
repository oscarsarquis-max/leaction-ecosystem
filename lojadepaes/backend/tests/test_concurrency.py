from threading import Barrier, Thread

from app.domain.errors import CapacityError
from app.domain.orders import confirm_order
from app.models.enums import OrderStatus
from app.models.orders import Order
from sqlalchemy.orm import Session, sessionmaker
from tests.db_fixtures import draft_order, priced_catalog


def test_two_confirms_cannot_exceed_last_unit(db: Session, test_engine) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 1
    catalog["slot"].capacity_units = 1
    first = draft_order(db, catalog)
    second = draft_order(db, catalog)
    db.commit()
    first_id, second_id = first.id, second.id
    barrier = Barrier(2)
    results: list[str] = []
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def worker(order_id) -> None:
        session = factory()
        try:
            barrier.wait(timeout=10)
            confirm_order(session, order_id)
            session.commit()
            results.append("ok")
        except CapacityError:
            session.rollback()
            results.append("capacity")
        finally:
            session.close()

    threads = [Thread(target=worker, args=(first_id,)), Thread(target=worker, args=(second_id,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert sorted(results) == ["capacity", "ok"]
    session = factory()
    statuses = {session.get(Order, first_id).status, session.get(Order, second_id).status}
    session.close()
    assert statuses == {OrderStatus.CONFIRMED.value, OrderStatus.DRAFT.value}
