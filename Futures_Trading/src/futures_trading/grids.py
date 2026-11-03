from __future__ import annotations

from typing import TypeVar


T = TypeVar("T")


def parse_float_grid(value: str | None, *, default: str | None = None) -> list[float]:
    raw = value if value not in {None, ""} else default
    if raw is None:
        raise ValueError("Grid cannot be empty")
    values: list[float] = []
    for part in str(raw).replace("\n", ",").replace(" ", ",").split(","):
        token = part.strip()
        if not token:
            continue
        values.extend(parse_float_token(token))
    if not values:
        raise ValueError("Grid cannot be empty")
    return dedupe_preserve_order(values)


def parse_optional_float_grid(value: str | None, *, default: str | None = None) -> list[float | None]:
    raw = value if value not in {None, ""} else default
    if raw is None or str(raw).strip().lower() in {"", "none", "null", "off"}:
        return [None]
    values: list[float | None] = []
    for part in str(raw).replace("\n", ",").replace(" ", ",").split(","):
        token = part.strip()
        if not token:
            continue
        if token.lower() in {"none", "null", "off"}:
            values.append(None)
        else:
            values.extend(parse_float_token(token))
    return dedupe_preserve_order(values) or [None]


def parse_float_token(token: str) -> list[float]:
    normalized = token.replace("..", ":")
    if ":" not in normalized:
        return [float(normalized)]

    pieces = [piece for piece in normalized.split(":") if piece != ""]
    if len(pieces) != 3:
        raise ValueError(f"Range '{token}' must use start:end:step")
    start, end, step = (float(piece) for piece in pieces)
    if step == 0:
        raise ValueError("Range step cannot be zero")
    if start < end and step < 0:
        raise ValueError("Range step must be positive when start is below end")
    if start > end and step > 0:
        raise ValueError("Range step must be negative when start is above end")

    values: list[float] = []
    current = start
    epsilon = abs(step) / 1_000_000
    if step > 0:
        while current <= end + epsilon:
            values.append(round_float(current))
            current += step
    else:
        while current >= end - epsilon:
            values.append(round_float(current))
            current += step
    return values


def dedupe_preserve_order(values: list[T]) -> list[T]:
    seen: set[T] = set()
    result: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def round_float(value: float) -> float:
    return round(value, 12)


def parse_int_grid(value: str | None, *, default: str | None = None) -> list[int]:
    """Parse comma/range grids into integers (for lengths, delays, integer tuning knobs)."""

    floats = parse_float_grid(value, default=default)
    ints = [int(round(item)) for item in floats]
    return dedupe_preserve_order(ints)
