from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import Settings

WEEKDAY_NAMES = {
    1: "segunda-feira",
    2: "terça-feira",
    3: "quarta-feira",
    4: "quinta-feira",
    5: "sexta-feira",
    6: "sábado",
    7: "domingo",
}

WEEKDAY_SHORT = {
    1: "segunda",
    2: "terça",
    3: "quarta",
    4: "quinta",
    5: "sexta",
    6: "sábado",
    7: "domingo",
}

MONTH_NAMES = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


def bakery_zone(settings: Settings) -> ZoneInfo:
    return ZoneInfo(settings.bakery_timezone)


def bakery_now(settings: Settings) -> datetime:
    return datetime.now(bakery_zone(settings))


def bakery_today(settings: Settings) -> date:
    return bakery_now(settings).date()


def week_monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_sunday(value: date) -> date:
    return week_monday(value) + timedelta(days=6)


def dates_in_week(week_start: date) -> list[date]:
    start = week_monday(week_start)
    return [start + timedelta(days=offset) for offset in range(7)]


def local_date_of(moment: datetime, settings: Settings) -> date:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(bakery_zone(settings)).date()


def format_long_date(value: date) -> str:
    return f"{WEEKDAY_NAMES[value.isoweekday()]}, {value.day} de {MONTH_NAMES[value.month]}"
