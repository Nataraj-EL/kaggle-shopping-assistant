# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from app.agent import (
    ADMIN_USERS,
    CARTS,
    DISCOUNT_CODES,
    LOYALTY_POINTS,
    REGISTERED_USERS,
    award_loyalty_points,
    process_cart_checkout,
    update_discount_status,
)


def test_award_loyalty_points_success() -> None:
    REGISTERED_USERS.add("TEST_USER_999")
    LOYALTY_POINTS["TEST_USER_999"] = 100

    try:
        res = award_loyalty_points(user_id="TEST_USER_999", points=50)
        assert "Success" in res
        assert LOYALTY_POINTS["TEST_USER_999"] == 150
    finally:
        REGISTERED_USERS.discard("TEST_USER_999")
        LOYALTY_POINTS.pop("TEST_USER_999", None)


def test_award_loyalty_points_unregistered() -> None:
    res = award_loyalty_points(user_id="UNREGISTERED_USER", points=50)
    assert "Award failed" in res
    assert "not registered" in res


def test_award_loyalty_points_validation_negative() -> None:
    res = award_loyalty_points(user_id="Nataraj-EL", points=-10)
    assert "Validation Error" in res


def test_award_loyalty_points_validation_zero() -> None:
    res = award_loyalty_points(user_id="Nataraj-EL", points=0)
    assert "Validation Error" in res


def test_award_loyalty_points_validation_empty_user() -> None:
    res = award_loyalty_points(user_id="", points=10)
    assert "Validation Error" in res


def test_process_cart_checkout_success() -> None:
    # Set up a test cart and user
    REGISTERED_USERS.add("TEST_CHECKOUT_USER")
    LOYALTY_POINTS["TEST_CHECKOUT_USER"] = 0
    CARTS["TEST_CART_1"] = {
        "user_id": "TEST_CHECKOUT_USER",
        "items": [{"name": "Item A", "price": 40.0}],
        "subtotal": 40.0,
        "is_processed": False,
    }

    try:
        res = process_cart_checkout(
            cart_id="TEST_CART_1", user_id="TEST_CHECKOUT_USER", discount_code=None
        )
        assert "Checkout Successful" in res
        assert "Final Total: $40.00" in res
        assert "New balance is 40 points" in res
        assert CARTS["TEST_CART_1"]["is_processed"] is True
    finally:
        REGISTERED_USERS.discard("TEST_CHECKOUT_USER")
        LOYALTY_POINTS.pop("TEST_CHECKOUT_USER", None)
        CARTS.pop("TEST_CART_1", None)


def test_process_cart_checkout_with_discount() -> None:
    REGISTERED_USERS.add("TEST_CHECKOUT_USER")
    LOYALTY_POINTS["TEST_CHECKOUT_USER"] = 0
    CARTS["TEST_CART_2"] = {
        "user_id": "TEST_CHECKOUT_USER",
        "items": [{"name": "Item B", "price": 50.0}],
        "subtotal": 50.0,
        "is_processed": False,
    }
    # Reset WELCOME50
    DISCOUNT_CODES["WELCOME50"] = {"is_redeemed": False, "redeemed_by": None, "is_active": True}

    try:
        res = process_cart_checkout(
            cart_id="TEST_CART_2",
            user_id="TEST_CHECKOUT_USER",
            discount_code="WELCOME50",
        )
        assert "Checkout Successful" in res
        assert "Discount Applied: $25.00" in res
        assert "Final Total: $25.00" in res
        assert "New balance is 25 points" in res
        assert DISCOUNT_CODES["WELCOME50"]["is_redeemed"] is True
    finally:
        REGISTERED_USERS.discard("TEST_CHECKOUT_USER")
        LOYALTY_POINTS.pop("TEST_CHECKOUT_USER", None)
        CARTS.pop("TEST_CART_2", None)
        DISCOUNT_CODES["WELCOME50"] = {"is_redeemed": False, "redeemed_by": None, "is_active": True}


def test_process_cart_checkout_mismatch_user() -> None:
    REGISTERED_USERS.add("USER123")
    REGISTERED_USERS.add("USER456")
    CARTS["TEST_CART_3"] = {
        "user_id": "USER123",
        "items": [{"name": "Item C", "price": 10.0}],
        "subtotal": 10.0,
        "is_processed": False,
    }

    try:
        res = process_cart_checkout(
            cart_id="TEST_CART_3", user_id="USER456", discount_code=None
        )
        assert "Checkout failed" in res
        assert "does not belong to user" in res
    finally:
        CARTS.pop("TEST_CART_3", None)


def test_process_cart_checkout_already_processed() -> None:
    REGISTERED_USERS.add("USER123")
    CARTS["TEST_CART_4"] = {
        "user_id": "USER123",
        "items": [{"name": "Item D", "price": 10.0}],
        "subtotal": 10.0,
        "is_processed": True,
    }

    try:
        res = process_cart_checkout(
            cart_id="TEST_CART_4", user_id="USER123", discount_code=None
        )
        assert "Checkout failed" in res
        assert "already been checked out" in res
    finally:
        CARTS.pop("TEST_CART_4", None)


def test_process_cart_checkout_invalid_discount() -> None:
    REGISTERED_USERS.add("USER123")
    CARTS["TEST_CART_5"] = {
        "user_id": "USER123",
        "items": [{"name": "Item E", "price": 10.0}],
        "subtotal": 10.0,
        "is_processed": False,
    }

    try:
        res = process_cart_checkout(
            cart_id="TEST_CART_5", user_id="USER123", discount_code="INVALID_CODE"
        )
        assert "Checkout failed" in res
        assert "Discount code 'INVALID_CODE' is invalid" in res
    finally:
        CARTS.pop("TEST_CART_5", None)


def test_update_discount_status_success() -> None:
    # Admin can deactivate and activate codes
    ADMIN_USERS.add("TEST_ADMIN")
    DISCOUNT_CODES["SUMMER20"] = {
        "is_redeemed": False,
        "redeemed_by": None,
        "is_active": True,
    }

    try:
        # Deactivate
        res = update_discount_status(
            code="SUMMER20", is_active=False, admin_user_id="TEST_ADMIN"
        )
        assert "Success" in res
        assert "deactivated" in res
        assert DISCOUNT_CODES["SUMMER20"]["is_active"] is False

        # Activate
        res2 = update_discount_status(
            code="SUMMER20", is_active=True, admin_user_id="TEST_ADMIN"
        )
        assert "Success" in res2
        assert "activated" in res2
        assert DISCOUNT_CODES["SUMMER20"]["is_active"] is True
    finally:
        ADMIN_USERS.discard("TEST_ADMIN")
        DISCOUNT_CODES["SUMMER20"] = {
            "is_redeemed": False,
            "redeemed_by": None,
            "is_active": True,
        }


def test_update_discount_status_unauthorized() -> None:
    # Non-admin user ID must fail privilege check
    res = update_discount_status(
        code="SUMMER20", is_active=False, admin_user_id="REGULAR_USER"
    )
    assert "Update failed" in res
    assert "not authorized as an administrator" in res
    assert DISCOUNT_CODES["SUMMER20"]["is_active"] is True


def test_redeem_discount_code_inactive() -> None:
    REGISTERED_USERS.add("USER123")
    DISCOUNT_CODES["SUMMER20"] = {
        "is_redeemed": False,
        "redeemed_by": None,
        "is_active": False,
    }

    try:
        from app.agent import redeem_discount_code

        res = redeem_discount_code(code="SUMMER20", user_id="USER123")
        assert "Redemption failed" in res
        assert "is inactive" in res
    finally:
        REGISTERED_USERS.discard("USER123")
        DISCOUNT_CODES["SUMMER20"] = {
            "is_redeemed": False,
            "redeemed_by": None,
            "is_active": True,
        }
