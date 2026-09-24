import pytest
from services.split_bill_engine import SplitBillEngine

def test_calculate_equal_split():
    items = [
        {"name": "Nasi Goreng", "subtotal": 40000.0},
        {"name": "Es Teh", "subtotal": 10000.0}
    ]
    participants = ["Alice", "Bob"]
    assignments = {} # default split equal

    res = SplitBillEngine.calculate_split(
        items=items,
        participants=participants,
        assignments=assignments,
        tax_amount=5000.0,
        service_charge=0.0,
        discount_amount=0.0
    )

    assert res["total_items_subtotal"] == 50000.0
    assert res["grand_total"] == 55000.0
    assert res["participants"]["Alice"]["items_subtotal"] == 25000.0
    assert res["participants"]["Bob"]["items_subtotal"] == 25000.0
    assert res["participants"]["Alice"]["final_amount"] == 27500.0
    assert res["participants"]["Bob"]["final_amount"] == 27500.0

def test_calculate_itemized_split_with_tax_and_discount():
    items = [
        {"name": "Pizza Super", "subtotal": 100000.0}, # Item 0
        {"name": "Salad", "subtotal": 40000.0}          # Item 1
    ]
    participants = ["Alice", "Bob"]
    assignments = {
        "0": ["Alice", "Bob"], # Pizza shared 50/50 -> 50k each
        "1": ["Alice"]         # Salad only Alice -> 40k
    }

    # Subtotals: Alice = 50k + 40k = 90k (64.28%), Bob = 50k (35.71%)
    res = SplitBillEngine.calculate_split(
        items=items,
        participants=participants,
        assignments=assignments,
        tax_amount=14000.0,
        service_charge=0.0,
        discount_amount=14000.0 # Tax and discount cancel out
    )

    assert res["total_items_subtotal"] == 140000.0
    assert res["grand_total"] == 140000.0
    assert res["participants"]["Alice"]["items_subtotal"] == 90000.0
    assert res["participants"]["Bob"]["items_subtotal"] == 50000.0
    assert res["participants"]["Alice"]["final_amount"] == 90000.0
    assert res["participants"]["Bob"]["final_amount"] == 50000.0

def test_split_bill_rounding_remainder():
    items = [
        {"name": "Item 1", "subtotal": 100.0}
    ]
    participants = ["A", "B", "C"] # 100 / 3 = 33.33...
    assignments = {}

    res = SplitBillEngine.calculate_split(
        items=items,
        participants=participants,
        assignments=assignments,
        tax_amount=0.0
    )

    # Sum of final amounts must equal 100.0 exactly!
    sum_final = sum(p["final_amount"] for p in res["participants"].values())
    assert sum_final == 100.0
