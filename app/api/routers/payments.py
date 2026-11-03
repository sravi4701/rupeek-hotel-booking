from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from app.api.dependencies import PaymentServiceDep
from app.api.schemas.payment import PaymentCreate, PaymentOut, PaymentResultOut

router = APIRouter(prefix="/bookings/{booking_id}/payments", tags=["payments"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        402: {"model": PaymentResultOut, "description": "Payment declined; booking still pending"},
        409: {"description": "Booking not awaiting payment, or Idempotency-Key reused"},
    },
)
def pay_for_booking(
    booking_id: str,
    body: PaymentCreate,
    service: PaymentServiceDep,
    response: Response,
    idempotency_key: Annotated[str | None, Header(max_length=255)] = None,
) -> PaymentResultOut:
    """Charge the booking. Success confirms it. A decline returns 402 and the guest can retry.

    Send an ``Idempotency-Key`` header to retry safely: a repeat returns the
    original result and is never charged twice.
    """
    outcome = service.pay(body.to_request(booking_id, idempotency_key))
    if outcome.payment.declined:
        response.status_code = status.HTTP_402_PAYMENT_REQUIRED
    if outcome.replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return PaymentResultOut.from_outcome(outcome)


@router.get("")
def list_payments(booking_id: str, service: PaymentServiceDep) -> list[PaymentOut]:
    """Every payment attempt for the booking, failed ones included, oldest first."""
    return [PaymentOut.from_domain(p) for p in service.list_payments(booking_id)]
