from __future__ import annotations

import re
from enum import StrEnum


class ExpenseCategory(StrEnum):
    FOOD_DINING = "Food & Dining"
    TRAVEL = "Travel"
    SOFTWARE_SUBSCRIPTIONS = "Software & Subscriptions"
    OFFICE_SUPPLIES = "Office Supplies"
    UTILITIES = "Utilities"
    RENT = "Rent"
    FEES_BANKING = "Fees & Banking"
    HEALTHCARE = "Healthcare"
    OTHER = "Other"


_CATEGORY_KEYWORDS = (
    (
        ExpenseCategory.FOOD_DINING,
        ("restaurant", "cafe", "coffee", "swiggy", "zomato", "doordash", "ubereats"),
    ),
    (
        ExpenseCategory.TRAVEL,
        ("uber", "lyft", "ola", "airbnb", "hotel", "airline", "flight", "railway", "taxi"),
    ),
    (
        ExpenseCategory.SOFTWARE_SUBSCRIPTIONS,
        ("netflix", "spotify", "adobe", "microsoft", "google", "aws", "github", "zoom", "slack"),
    ),
    (ExpenseCategory.OFFICE_SUPPLIES, ("amazon", "staples", "office depot", "walmart", "target")),
    (ExpenseCategory.UTILITIES, ("electric", "electricity", "water", "gas utility", "internet", "telecom", "power")),
    (ExpenseCategory.RENT, ("rent", "property management", "landlord")),
    (ExpenseCategory.FEES_BANKING, ("bank fee", "service charge", "processing fee", "wire fee", "atm fee")),
    (ExpenseCategory.HEALTHCARE, ("pharmacy", "hospital", "clinic", "medical", "healthcare")),
)


class CategoryClassifier:
    def classify(self, merchant: str) -> ExpenseCategory:
        normalized = _normalize(merchant)
        for category, keywords in _CATEGORY_KEYWORDS:
            if any(_normalize(keyword) in normalized for keyword in keywords):
                return category
        return ExpenseCategory.OTHER


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
