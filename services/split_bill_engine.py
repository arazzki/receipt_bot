import math
from typing import Dict, List, Any, Optional

class SplitBillEngine:
    """
    Split Bill Calculation Engine supporting multi-item assignment,
    equal sharing, and proportional allocation of Tax, Service Charge, and Discounts.
    """

    @staticmethod
    def calculate_split(
        items: List[Dict[str, Any]],
        participants: List[str],
        assignments: Dict[str, List[str]], # map item_index or item_name -> list of participant names
        tax_amount: float = 0.0,
        service_charge: float = 0.0,
        discount_amount: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates exact split bill for each participant.

        :param items: List of dicts e.g. [{"name": "Nasi Goreng", "price": 30000, "qty": 1, "subtotal": 30000}]
        :param participants: List of participant names ["Alice", "Bob", "Charlie"]
        :param assignments: Dict mapping item index or name to assigned participants, e.g. {"0": ["Alice"], "1": ["Alice", "Bob"]}
        :param tax_amount: Total tax amount (PPN/PB1)
        :param service_charge: Total service charge
        :param discount_amount: Total discount amount
        """
        if not participants:
            return {"error": "No participants provided."}

        # Initialize participant subtotals
        participant_subtotals: Dict[str, float] = {p: 0.0 for p in participants}
        item_breakdowns: List[Dict[str, Any]] = []

        total_items_subtotal = 0.0

        for idx, item in enumerate(items):
            item_id = str(idx)
            item_name = item.get("name") or item.get("item_name") or f"Item {idx+1}"
            subtotal = float(item.get("subtotal", item.get("price", 0.0) * item.get("qty", 1.0)))
            total_items_subtotal += subtotal

            assigned = assignments.get(item_id) or assignments.get(item_name)
            # Default to split among all if unassigned
            if not assigned:
                assigned = participants

            num_assigned = len(assigned)
            share_per_person = subtotal / num_assigned if num_assigned > 0 else 0.0

            for p in assigned:
                if p in participant_subtotals:
                    participant_subtotals[p] += share_per_person

            item_breakdowns.append({
                "item_name": item_name,
                "subtotal": subtotal,
                "assigned_to": assigned,
                "share_per_person": share_per_person
            })

        # Calculate proportional extras
        net_extra = tax_amount + service_charge - discount_amount
        participant_results: Dict[str, Dict[str, float]] = {}

        total_calculated_grand = 0.0

        for p, sub in participant_subtotals.items():
            proportion = (sub / total_items_subtotal) if total_items_subtotal > 0 else (1.0 / len(participants))
            
            p_tax = round(tax_amount * proportion, 2)
            p_service = round(service_charge * proportion, 2)
            p_discount = round(discount_amount * proportion, 2)
            p_final = round(sub + p_tax + p_service - p_discount, 2)

            participant_results[p] = {
                "items_subtotal": round(sub, 2),
                "tax_share": p_tax,
                "service_share": p_service,
                "discount_share": p_discount,
                "final_amount": p_final
            }
            total_calculated_grand += p_final

        # Check for rounding remainder against grand total
        expected_grand = round(total_items_subtotal + tax_amount + service_charge - discount_amount, 2)
        remainder = round(expected_grand - total_calculated_grand, 2)

        # Distribute 1-cent/rupiah remainder to participant with highest subtotal if needed
        if remainder != 0 and participants:
            top_participant = max(participant_subtotals, key=participant_subtotals.get)
            participant_results[top_participant]["final_amount"] = round(
                participant_results[top_participant]["final_amount"] + remainder, 2
            )

        return {
            "total_items_subtotal": round(total_items_subtotal, 2),
            "tax_amount": tax_amount,
            "service_charge": service_charge,
            "discount_amount": discount_amount,
            "grand_total": expected_grand,
            "participants": participant_results,
            "item_breakdowns": item_breakdowns
        }
