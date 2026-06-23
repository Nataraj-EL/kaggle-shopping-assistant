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

from app.agent import DISCOUNT_CODES, REGISTERED_USERS, redeem_discount_code


def test_redeem_discount_code_success() -> None:
    # Set up
    REGISTERED_USERS.add("TEST_USER_RED")
    DISCOUNT_CODES["TEST_CODE_1"] = {
        "is_redeemed": False,
        "redeemed_by": None,
        "is_active": True,
    }

    try:
        res = redeem_discount_code(code="TEST_CODE_1", user_id="TEST_USER_RED")
        assert "Success" in res
        assert DISCOUNT_CODES["TEST_CODE_1"]["is_redeemed"] is True
        assert DISCOUNT_CODES["TEST_CODE_1"]["redeemed_by"] == "TEST_USER_RED"
    finally:
        # Clean up
        REGISTERED_USERS.discard("TEST_USER_RED")
        DISCOUNT_CODES.pop("TEST_CODE_1", None)


def test_redeem_discount_code_empty_user_id() -> None:
    res = redeem_discount_code(code="WELCOME50", user_id="")
    assert "Redemption failed" in res
    assert "User ID is required" in res


def test_redeem_discount_code_unregistered_user() -> None:
    res = redeem_discount_code(code="WELCOME50", user_id="NOT_A_USER")
    assert "Redemption failed" in res
    assert "not registered" in res


def test_redeem_discount_code_invalid_code() -> None:
    REGISTERED_USERS.add("TEST_USER_RED")
    try:
        res = redeem_discount_code(code="INVALID_CODE", user_id="TEST_USER_RED")
        assert "Redemption failed" in res
        assert "is invalid" in res
    finally:
        REGISTERED_USERS.discard("TEST_USER_RED")


def test_redeem_discount_code_inactive() -> None:
    REGISTERED_USERS.add("TEST_USER_RED")
    DISCOUNT_CODES["TEST_CODE_INACTIVE"] = {
        "is_redeemed": False,
        "redeemed_by": None,
        "is_active": False,
    }

    try:
        res = redeem_discount_code(code="TEST_CODE_INACTIVE", user_id="TEST_USER_RED")
        assert "Redemption failed" in res
        assert "is inactive" in res
    finally:
        REGISTERED_USERS.discard("TEST_USER_RED")
        DISCOUNT_CODES.pop("TEST_CODE_INACTIVE", None)


def test_redeem_discount_code_already_redeemed() -> None:
    REGISTERED_USERS.add("TEST_USER_RED")
    DISCOUNT_CODES["TEST_CODE_REDEEMED"] = {
        "is_redeemed": True,
        "redeemed_by": "SOME_OTHER_USER",
        "is_active": True,
    }

    try:
        res = redeem_discount_code(code="TEST_CODE_REDEEMED", user_id="TEST_USER_RED")
        assert "Redemption failed" in res
        assert "already been redeemed" in res
    finally:
        REGISTERED_USERS.discard("TEST_USER_RED")
        DISCOUNT_CODES.pop("TEST_CODE_REDEEMED", None)
