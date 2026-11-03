import pytest

from app.domain.common.exceptions import DomainValidationError
from app.strategies.payments.card import CardPayment, passes_luhn
from app.strategies.payments.registry import default_payment_methods
from app.strategies.payments.upi import UpiPayment
from app.strategies.payments.wallet import WalletPayment


class TestCard:
    def test_parses_and_masks_valid_card(self) -> None:
        instrument = CardPayment().parse({"card_number": "4242 4242 4242 4242", "cvv": "123"})

        assert instrument.method == "card"
        assert instrument.token == "4242424242424242"
        assert instrument.display == "card ****4242"

    @pytest.mark.parametrize(
        "details",
        [
            {"card_number": "4242424242424241", "cvv": "123"},  # fails Luhn
            {"card_number": "4242", "cvv": "123"},
            {"card_number": "4242424242424242", "cvv": "12"},
            {"card_number": "4242424242424242"},
            {},
        ],
        ids=["luhn", "too-short", "bad-cvv", "no-cvv", "empty"],
    )
    def test_rejects_invalid_details(self, details: dict[str, str]) -> None:
        with pytest.raises(DomainValidationError):
            CardPayment().parse(details)

    @pytest.mark.parametrize(
        ("number", "valid"),
        [("4242424242424242", True), ("4000000000000002", True), ("1234", False)],
    )
    def test_luhn(self, number: str, valid: bool) -> None:
        assert passes_luhn(number) is valid


class TestUpi:
    def test_parses_vpa(self) -> None:
        assert UpiPayment().parse({"vpa": "Asha.Rao@okhdfc"}).token == "asha.rao@okhdfc"

    @pytest.mark.parametrize("vpa", ["asha", "asha@", "@bank", "a@b1"])
    def test_rejects_invalid_vpa(self, vpa: str) -> None:
        with pytest.raises(DomainValidationError):
            UpiPayment().parse({"vpa": vpa})


class TestWallet:
    def test_parses_wallet(self) -> None:
        instrument = WalletPayment().parse({"provider": "PayTM", "phone": "9876543210"})

        assert instrument.token == "paytm:9876543210"
        assert instrument.display == "paytm ******3210"

    @pytest.mark.parametrize(
        "details",
        [{"provider": "cashapp", "phone": "9876543210"}, {"provider": "paytm", "phone": "12345"}],
        ids=["provider", "phone"],
    )
    def test_rejects_invalid_details(self, details: dict[str, str]) -> None:
        with pytest.raises(DomainValidationError):
            WalletPayment().parse(details)


class TestRegistry:
    def test_resolves_methods_case_insensitively(self) -> None:
        registry = default_payment_methods()

        assert registry.names() == ["card", "upi", "wallet"]
        assert isinstance(registry.get("UPI"), UpiPayment)

    def test_unknown_method_is_a_validation_error(self) -> None:
        with pytest.raises(DomainValidationError, match="Unsupported payment method"):
            default_payment_methods().get("bitcoin")
