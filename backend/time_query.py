from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Iterable, Optional


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "did",
    "doing",
    "for",
    "from",
    "i",
    "in",
    "me",
    "my",
    "of",
    "on",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
}

_TIME_RE = re.compile(
    r"\b(?:at|around|about)?\s*(?P<hour>\d{1,2})(?::(?P<minute>[0-5]\d))?\s*(?P<ampm>[ap])\.?m\.?\b",
    re.IGNORECASE,
)
_CLOCK_RE = re.compile(r"\b(?:at|around|about)?\s*(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class TimeQuery:
    start_utc: datetime
    end_utc: datetime
    day_start_utc: datetime
    day_end_utc: datetime
    center_utc: Optional[datetime]
    cleaned_query: str
    label: str


def parse_time_query(query: str, now: Optional[datetime] = None) -> Optional[TimeQuery]:
    text = " ".join(query.lower().split())
    local_now = _local_now(now)
    date_anchor = _date_anchor(text, local_now)
    clock_value = _clock_value(text)

    if date_anchor is None and clock_value is None:
        return None

    if date_anchor is None:
        date_anchor = local_now.date()

    if clock_value is None:
        day_start_local = datetime.combine(date_anchor, time.min, tzinfo=local_now.tzinfo)
        day_end_local = day_start_local + timedelta(days=1)
        start_local = day_start_local
        end_local = day_end_local
        center_local = None
        label = _format_label(start_local)
    else:
        day_start_local = datetime.combine(date_anchor, time.min, tzinfo=local_now.tzinfo)
        day_end_local = day_start_local + timedelta(days=1)
        center_local = datetime.combine(date_anchor, clock_value, tzinfo=local_now.tzinfo)
        start_local = center_local - timedelta(minutes=90)
        end_local = center_local + timedelta(minutes=90)
        label = _format_label(center_local, include_time=True)

    return TimeQuery(
        start_utc=start_local.astimezone(timezone.utc),
        end_utc=end_local.astimezone(timezone.utc),
        day_start_utc=day_start_local.astimezone(timezone.utc),
        day_end_utc=day_end_local.astimezone(timezone.utc),
        center_utc=center_local.astimezone(timezone.utc) if center_local else None,
        cleaned_query=_clean_temporal_terms(text),
        label=label,
    )


def parse_capture_timestamp(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def temporal_score(timestamp: datetime, time_query: TimeQuery) -> float:
    if timestamp < time_query.start_utc or timestamp > time_query.end_utc:
        return 0.0
    if time_query.center_utc is None:
        return 0.8
    half_window = max((time_query.end_utc - time_query.center_utc).total_seconds(), 1.0)
    distance = abs((timestamp - time_query.center_utc).total_seconds())
    return max(0.05, 1.0 - (distance / half_window))


def same_day_fallback_score(timestamp: datetime, time_query: TimeQuery) -> float:
    if timestamp < time_query.day_start_utc or timestamp > time_query.day_end_utc:
        return 0.0
    if time_query.center_utc is None:
        return 0.8
    distance = abs((timestamp - time_query.center_utc).total_seconds())
    twelve_hours = 12 * 60 * 60
    return max(0.08, 0.55 * (1.0 - min(distance / twelve_hours, 1.0)))


def text_score(fields: Iterable[object], query: str) -> float:
    terms = [term for term in _TOKEN_RE.findall(query.lower()) if term not in _STOP_WORDS]
    if not terms:
        return 0.0
    haystack = " ".join(str(field or "").lower() for field in fields)
    unique_terms = sorted(set(terms))
    hits = sum(1 for term in unique_terms if term in haystack)
    return hits / max(len(unique_terms), 1)


def _local_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now().astimezone()
    if now.tzinfo is None:
        return now.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return now.astimezone()


def _date_anchor(text: str, now: datetime):
    if "day before yesterday" in text:
        return now.date() - timedelta(days=2)
    if "yesterday" in text:
        return now.date() - timedelta(days=1)
    if "today" in text or "this morning" in text or "this afternoon" in text or "tonight" in text:
        return now.date()
    return None


def _clock_value(text: str) -> Optional[time]:
    match = _TIME_RE.search(text)
    if match:
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or "0")
        ampm = match.group("ampm").lower()
        if hour < 1 or hour > 12:
            return None
        if ampm == "p" and hour != 12:
            hour += 12
        if ampm == "a" and hour == 12:
            hour = 0
        return time(hour=hour, minute=minute)

    match = _CLOCK_RE.search(text)
    if match:
        return time(hour=int(match.group("hour")), minute=int(match.group("minute")))
    return None


def _clean_temporal_terms(text: str) -> str:
    cleaned = _TIME_RE.sub(" ", text)
    cleaned = _CLOCK_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\b(day before yesterday|yesterday|today|this morning|this afternoon|tonight)\b", " ", cleaned)
    terms = [term for term in _TOKEN_RE.findall(cleaned) if term not in _STOP_WORDS]
    return " ".join(terms)


def _format_label(value: datetime, include_time: bool = False) -> str:
    date_text = value.strftime("%b %d").replace(" 0", " ")
    if not include_time:
        return date_text
    time_text = value.strftime("%I:%M %p").lstrip("0")
    return f"{date_text}, {time_text}"
