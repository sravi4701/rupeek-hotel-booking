"""Lock keys shared by services, so they all use the same lock for the same resource.

Lock order, to avoid deadlocks: idempotency key -> booking -> inventory.
"""


def idempotency_lock(key: str) -> tuple[str, str]:
    return ("idempotency", key)


def booking_lock(booking_id: str) -> tuple[str, str]:
    return ("booking", booking_id)


def inventory_lock(property_id: str, room_type_id: str) -> tuple[str, str, str]:
    return ("inventory", property_id, room_type_id)
