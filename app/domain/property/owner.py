from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.ids import new_id


class AccountType(StrEnum):
    INDIVIDUAL = "individual"
    CHAIN = "chain"


@dataclass(slots=True)
class OwnerAccount:
    """An account that owns one or more properties.

    A standalone hotel is an account with a single property. It goes through the
    same onboarding path as a chain, with no separate code path. ``account_type``
    only describes the account. It does not change behaviour.
    """

    name: str
    account_type: AccountType = AccountType.INDIVIDUAL
    property_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Owner name is required")

    def add_property(self, property_id: str) -> None:
        if property_id in self.property_ids:
            raise DomainValidationError(f"Property '{property_id}' already belongs to owner")
        self.property_ids.append(property_id)
