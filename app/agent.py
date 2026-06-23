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

import os
from functools import cached_property
from typing import TypedDict

import dotenv
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import Client, types
from pydantic import BaseModel, Field, ValidationError

dotenv.load_dotenv()


# We set environment variables needed by ADK, but we'll override the Client with our mock API key
try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "mock-project"

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"


# Subclass Gemini to explicitly initialize the API client with the simulated hardcoded API key
class CustomGemini(Gemini):
    api_key: str = os.getenv("GEMINI_API_KEY") or "AIzaSyD-mock-key-value-12345"

    @cached_property
    def api_client(self) -> Client:
        return Client(api_key=self.api_key)

    @cached_property
    def _live_api_client(self) -> Client:
        return Client(api_key=self.api_key)


# In-memory store for single-use discount codes
# Format: {code: {"is_redeemed": bool, "redeemed_by": str | None, "is_active": bool}}
DISCOUNT_CODES = {
    "WELCOME50": {"is_redeemed": False, "redeemed_by": None, "is_active": True},
    "SUMMER20": {"is_redeemed": False, "redeemed_by": None, "is_active": True},
}

# Registered administrators who are allowed to update discount status
ADMIN_USERS = {"Nataraj-EL"}


# Registered users who are allowed to redeem codes and earn points
REGISTERED_USERS = {"USER123", "Nataraj-EL", "USER456", "user_123"}


# In-memory store for customer loyalty points balance
LOYALTY_POINTS = {
    "USER123": 100,
    "Nataraj-EL": 250,
    "USER456": 50,
}


class Item(TypedDict):
    name: str
    price: float


class Cart(TypedDict):
    user_id: str
    items: list[Item]
    subtotal: float
    is_processed: bool


# In-memory store for customer shopping carts
CARTS: dict[str, Cart] = {
    "CART123": {
        "user_id": "USER123",
        "items": [{"name": "Shirt", "price": 30.0}],
        "subtotal": 30.0,
        "is_processed": False,
    },
    "CART456": {
        "user_id": "Nataraj-EL",
        "items": [{"name": "Shoes", "price": 100.0}],
        "subtotal": 100.0,
        "is_processed": False,
    },
}


class ProcessCartCheckoutInput(BaseModel):
    cart_id: str = Field(
        ..., min_length=1, description="The unique ID of the shopping cart to checkout."
    )
    discount_code: str | None = Field(
        None, description="An optional discount code to apply to the checkout."
    )
    user_id: str = Field(
        ..., min_length=1, description="The registered user ID of the customer."
    )


class AwardLoyaltyPointsInput(BaseModel):
    user_id: str = Field(
        ..., min_length=1, description="The registered user ID of the customer."
    )
    points: int = Field(
        ...,
        gt=0,
        description="The number of loyalty points to award (must be greater than 0).",
    )


class UpdateDiscountStatusInput(BaseModel):
    code: str = Field(..., min_length=1, description="The discount code to update.")
    is_active: bool = Field(
        ..., description="Whether to activate (True) or deactivate (False) the code."
    )
    admin_user_id: str = Field(
        ...,
        min_length=1,
        description="The user ID of the administrator making the update.",
    )


def award_loyalty_points(user_id: str, points: int) -> str:
    """Awards loyalty points to a registered user's account after a successful purchase.

    Args:
        user_id: The registered user ID of the customer (e.g., 'USER123').
        points: The number of loyalty points to award (must be a positive integer).

    Returns:
        A string indicating if the points were successfully awarded or the reason for failure.
    """
    try:
        inputs = AwardLoyaltyPointsInput(user_id=user_id, points=points)
    except ValidationError as e:
        return f"Validation Error: {e.errors()}"

    user_id_clean = inputs.user_id.strip()

    if user_id_clean not in REGISTERED_USERS:
        return f"Award failed: User ID '{user_id_clean}' is not registered."

    current_points = LOYALTY_POINTS.get(user_id_clean, 0)
    new_points = current_points + inputs.points
    LOYALTY_POINTS[user_id_clean] = new_points

    return f"Success: Awarded {inputs.points} loyalty points to user '{user_id_clean}'. New balance is {new_points} points."


def process_cart_checkout(cart_id: str, user_id: str, discount_code: str | None) -> str:
    """Processes the checkout for a shopping cart, applying discounts and awarding points.

    Args:
        cart_id: The ID of the cart to checkout (e.g., 'CART123').
        user_id: The registered user ID of the customer (e.g., 'USER123').
        discount_code: Optional discount code to apply (e.g., 'WELCOME50').

    Returns:
        A string summarizing the checkout invoice details and points awarded, or error reason.
    """
    try:
        inputs = ProcessCartCheckoutInput(
            cart_id=cart_id, discount_code=discount_code, user_id=user_id
        )
    except ValidationError as e:
        return f"Validation Error: {e.errors()}"

    user_id_clean = inputs.user_id.strip()
    cart_id_clean = inputs.cart_id.strip()

    if user_id_clean not in REGISTERED_USERS:
        return f"Checkout failed: User ID '{user_id_clean}' is not registered."

    if cart_id_clean not in CARTS:
        return f"Checkout failed: Cart ID '{cart_id_clean}' does not exist."

    cart = CARTS[cart_id_clean]

    if cart["is_processed"]:
        return f"Checkout failed: Cart '{cart_id_clean}' has already been checked out."

    if cart["user_id"] != user_id_clean:
        return f"Checkout failed: Cart '{cart_id_clean}' does not belong to user '{user_id_clean}'."

    subtotal = cart["subtotal"]
    discount_amt = 0.0
    applied_code_msg = "None"

    if inputs.discount_code:
        code_res = redeem_discount_code(inputs.discount_code, user_id_clean)
        if "Success" not in code_res:
            return f"Checkout failed: {code_res}"

        code_upper = inputs.discount_code.strip().upper()
        applied_code_msg = code_upper
        if code_upper == "WELCOME50":
            discount_amt = subtotal * 0.5
        elif code_upper == "SUMMER20":
            discount_amt = subtotal * 0.2
        else:
            discount_amt = 0.0

    final_total = subtotal - discount_amt
    points_to_award = int(final_total)

    cart["is_processed"] = True

    award_res = "No points awarded (final total is too low)."
    if points_to_award > 0:
        award_res = award_loyalty_points(user_id_clean, points_to_award)

    items_summary = ", ".join([item["name"] for item in cart["items"]])

    return (
        f"Checkout Successful!\n"
        f"Cart ID: {cart_id_clean}\n"
        f"Items: {items_summary}\n"
        f"Subtotal: ${subtotal:.2f}\n"
        f"Applied Discount Code: {applied_code_msg}\n"
        f"Discount Applied: ${discount_amt:.2f}\n"
        f"Final Total: ${final_total:.2f}\n"
        f"Loyalty Points Update: {award_res}"
    )


def redeem_discount_code(code: str, user_id: str) -> str:
    """Redeems a single-use discount code for a registered user ID.

    Args:
        code: The discount code to redeem (e.g., 'WELCOME50', 'SUMMER20').
        user_id: The registered user ID of the customer (e.g., 'USER123').

    Returns:
        A string indicating if the redemption was successful or the reason for failure.
    """
    code_upper = code.strip().upper()
    user_id_clean = user_id.strip()

    if not user_id_clean:
        return "Redemption failed: User ID is required."

    if user_id_clean not in REGISTERED_USERS:
        return f"Redemption failed: User ID '{user_id_clean}' is not registered."

    if code_upper not in DISCOUNT_CODES:
        return f"Redemption failed: Discount code '{code}' is invalid."

    code_info = DISCOUNT_CODES[code_upper]
    if not code_info["is_active"]:
        return f"Redemption failed: Discount code '{code_upper}' is inactive."

    if code_info["is_redeemed"]:
        return f"Redemption failed: Discount code '{code_upper}' has already been redeemed."

    # Mark as redeemed
    code_info["is_redeemed"] = True
    code_info["redeemed_by"] = user_id_clean
    return f"Success: Discount code '{code_upper}' has been successfully redeemed for user '{user_id_clean}'!"


def update_discount_status(code: str, is_active: bool, admin_user_id: str) -> str:
    """Allows administrators to activate or deactivate single-use discount codes.

    Args:
        code: The discount code to update (e.g., 'WELCOME50').
        is_active: Whether to activate (True) or deactivate (False) the code.
        admin_user_id: The user ID of the administrator making the update (e.g., 'Nataraj-EL').

    Returns:
        A string indicating if the update was successful or the reason for failure.
    """
    try:
        inputs = UpdateDiscountStatusInput(
            code=code, is_active=is_active, admin_user_id=admin_user_id
        )
    except ValidationError as e:
        return f"Validation Error: {e.errors()}"

    admin_user_clean = inputs.admin_user_id.strip()
    code_upper = inputs.code.strip().upper()

    if admin_user_clean not in ADMIN_USERS:
        return f"Update failed: User ID '{admin_user_clean}' is not authorized as an administrator."

    if code_upper not in DISCOUNT_CODES:
        return f"Update failed: Discount code '{inputs.code}' is invalid."

    DISCOUNT_CODES[code_upper]["is_active"] = inputs.is_active
    status_str = "activated" if inputs.is_active else "deactivated"
    return f"Success: Discount code '{code_upper}' has been successfully {status_str}."


root_agent = Agent(
    name="root_agent",
    model=CustomGemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an AI shopping assistant for a retail store. "
        "You can help customers browse products, ask about promotions, and redeem discount codes. "
        "You also support checking out shopping carts and automatically awarding loyalty points to customers after checkout. "
        "Additionally, you support administrative updates to discount codes. "
        "When a user asks to redeem a discount code, you MUST ask for their registered user ID and call the `redeem_discount_code` tool. "
        "When a user completes a successful purchase, you MUST ask for their registered user ID and call the `award_loyalty_points` tool. "
        "When a user wants to check out their shopping cart, you MUST ask for their registered user ID and call the `process_cart_checkout` tool, optionally applying any discount code they provide. "
        "When an administrator wants to activate or deactivate a discount code, you MUST ask for their administrator user ID and call the `update_discount_status` tool. "
        "Always communicate the success or error message returned by the tools clearly."
    ),
    tools=[
        redeem_discount_code,
        award_loyalty_points,
        process_cart_checkout,
        update_discount_status,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
