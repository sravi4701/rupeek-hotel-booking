from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.application.booking_service import BookingRequest
from app.domain.booking.booking import Booking
from app.domain.booking.status import BookingStatus
from app.domain.common.date_range import DateRange


class BookingCreate(BaseModel):
    property_id: str
    room_type_id: str
    guest_name: str = Field(min_length=1, examples=["Asha Rao"])
    check_in: date
    check_out: date
    guests: int = Field(ge=1)
    rooms: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self

    def to_request(self) -> BookingRequest:
        return BookingRequest(
            property_id=self.property_id,
            room_type_id=self.room_type_id,
            guest_name=self.guest_name,
            stay=DateRange(self.check_in, self.check_out),
            guests=self.guests,
            rooms=self.rooms,
        )


class BookingOut(BaseModel):
    id: str
    status: BookingStatus
    property_id: str
    room_type_id: str
    guest_name: str
    check_in: date
    check_out: date
    nights: int
    guests: int
    rooms: int
    total_price: Decimal
    currency: str
    payment_id: str | None
    failed_payment_attempts: int
    refund_amount: Decimal | None
    created_at: datetime
    cancelled_at: datetime | None

    @classmethod
    def from_domain(cls, booking: Booking) -> BookingOut:
        return cls(
            id=booking.id,
            status=booking.status,
            property_id=booking.property_id,
            room_type_id=booking.room_type_id,
            guest_name=booking.guest_name,
            check_in=booking.stay.check_in,
            check_out=booking.stay.check_out,
            nights=booking.stay.night_count,
            guests=booking.guests,
            rooms=booking.rooms,
            total_price=booking.total_price.amount,
            currency=booking.total_price.currency,
            payment_id=booking.payment_id,
            failed_payment_attempts=booking.failed_payment_attempts,
            refund_amount=booking.refund_amount.amount if booking.refund_amount else None,
            created_at=booking.created_at,
            cancelled_at=booking.cancelled_at,
        )
