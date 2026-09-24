import re
import datetime
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Known Indonesian Brands/Merchants for Quick Matching
KNOWN_MERCHANTS = [
    "INDOMARET", "ALFAMART", "ALFAMIDI", "LAWSON", "CIRCLE K",
    "SUPERINDO", "HYPERMART", "TRANSMART", "CARREFOUR", "FARMERS MARKET",
    "STARBUCKS", "SOLARIA", "HOKBEN", "MCDONALDS", "MCDONALD'S", "KFC",
    "PIZZA HUT", "DOMINOS PIZZA", "BURGER KING", "D'COST", "WARUNK UPNORMAL",
    "JANJI JIWA", "KOPI KENANGAN", "MIXUE", "CHATIME", "EXCELSO", "KOI THE",
    "YOSHINOYA", "SHIHLIN", "HAUS", "POINT COFFEE"
]

INDONESIAN_MONTHS = {
    "jan": 1, "januari": 1,
    "feb": 2, "februari": 2,
    "mar": 3, "maret": 3,
    "apr": 4, "april": 4,
    "mei": 5, "may": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "agu": 8, "agus": 8, "agustus": 8, "aug": 8,
    "sep": 9, "september": 9,
    "okt": 10, "oktober": 10, "oct": 10,
    "nov": 11, "november": 11,
    "des": 12, "desember": 12, "dec": 12
}

class ReceiptParser:
    def __init__(self):
        pass

    def clean_number(self, val_str: str) -> float:
        """Normalizes Indonesian currency number string to float."""
        if not val_str:
            return 0.0
        
        # Remove currency symbols and non-essential text
        cleaned = re.sub(r"[^\d,\.]", "", val_str)
        if not cleaned:
            return 0.0

        # Handle formatting with thousands separators and decimals
        # e.g., 150.000,00 or 150,000.00 or 150000
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                # European/Indonesian format: 150.000,00
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # US format: 150,000.00
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Check if comma is decimal (2 digits after comma) or thousand separator
            parts = cleaned.split(",")
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "." in cleaned:
            parts = cleaned.split(".")
            # If single dot with 3 digits following, it's likely thousand separator (e.g. 50.000)
            if len(parts) > 1 and len(parts[-1]) == 3 and len(parts[0]) > 0:
                cleaned = cleaned.replace(".", "")
            elif len(parts) > 2:
                cleaned = cleaned.replace(".", "")

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def parse_merchant(self, text_lines: List[str]) -> str:
        """Extracts merchant or store name."""
        full_text_upper = "\n".join(text_lines[:10]).upper()

        # Check known brands
        for brand in KNOWN_MERCHANTS:
            if brand in full_text_upper:
                return brand.title()

        # Fallback: scan first 5 lines for non-generic header
        ignore_keywords = [
            "STRUK", "NOTA", "RECEIPT", "SELAMAT", "DATANG", "KASIR",
            "TELP", "JALAN", "JL.", "NO.", "TAX", "INV", "WELCOME"
        ]

        for line in text_lines[:5]:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 3:
                continue
            line_upper = line_clean.upper()
            if not any(kw in line_upper for kw in ignore_keywords) and not re.search(r"^\d+$", line_clean):
                return line_clean.title()

        return "Struk Belanja"

    def parse_date(self, text: str) -> datetime.date:
        """Extracts transaction date from OCR text."""
        # 1. Matches DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD
        date_pattern1 = r"\b(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{2,4})\b"
        match1 = re.search(date_pattern1, text)
        if match1:
            d, m, y = match1.groups()
            y_int = int(y)
            if y_int < 100:
                y_int += 2000
            try:
                # Check if first group is day or year
                if int(d) > 12:
                    return datetime.date(y_int, int(m), int(d))
                else:
                    return datetime.date(y_int, int(m), int(d))
            except ValueError:
                pass

        # 2. Matches YYYY-MM-DD
        date_pattern2 = r"\b(\d{4})[\/\.-](\d{1,2})[\/\.-](\d{1,2})\b"
        match2 = re.search(date_pattern2, text)
        if match2:
            y, m, d = match2.groups()
            try:
                return datetime.date(int(y), int(m), int(d))
            except ValueError:
                pass

        # 3. Matches DD MMM YYYY (e.g., 24 Sep 2026)
        date_pattern3 = r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})\b"
        match3 = re.search(date_pattern3, text, re.IGNORECASE)
        if match3:
            d, month_str, y = match3.groups()
            month_key = month_str.lower()[:3]
            m_int = INDONESIAN_MONTHS.get(month_key, 0)
            y_int = int(y)
            if y_int < 100:
                y_int += 2000
            if m_int > 0:
                try:
                    return datetime.date(y_int, m_int, int(d))
                except ValueError:
                    pass

        return datetime.date.today()

    def parse_total(self, text_lines: List[str]) -> float:
        """Extracts grand total amount from OCR text."""
        total_keywords = ["GRAND TOTAL", "TOTAL BAYAR", "TOTAL", "JUMLAH", "NETT", "NET TOTAL", "MUST PAY", "TAGIHAN"]
        exclude_keywords = ["TUNAI", "CASH", "KEMBALI", "CHANGE", "DEBIT", "KARTU", "SUBTOTAL", "SAVED"]

        candidate_amounts = []

        for line in reversed(text_lines):
            line_upper = line.upper()

            # Skip lines with exclude keywords if not containing grand total
            if any(ex in line_upper for ex in exclude_keywords) and not ("GRAND TOTAL" in line_upper or "TOTAL BAYAR" in line_upper):
                continue

            if any(kw in line_upper for kw in total_keywords):
                # Extract all number patterns from line
                matches = re.findall(r"(?:Rp\.?\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?|\d+)", line)
                for m in matches:
                    val = self.clean_number(m)
                    if val > 0:
                        candidate_amounts.append((val, line_upper))

        if candidate_amounts:
            # Prioritize GRAND TOTAL / TOTAL BAYAR
            for val, line_str in candidate_amounts:
                if "GRAND TOTAL" in line_str or "TOTAL BAYAR" in line_str:
                    return val
            return candidate_amounts[0][0]

        # Fallback: Find largest number in bottom half of receipt
        bottom_lines = text_lines[len(text_lines)//2:] if len(text_lines) > 2 else text_lines
        numbers = []
        for line in bottom_lines:
            line_upper = line.upper()
            if any(ex in line_upper for ex in exclude_keywords):
                continue
            matches = re.findall(r"(?:Rp\.?\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?|\d+)", line)
            for m in matches:
                val = self.clean_number(m)
                if 100 <= val <= 100000000: # Reasonable range for receipt total
                    numbers.append(val)

        return max(numbers) if numbers else 0.0

    def parse_tax_service_discount(self, text_lines: List[str]) -> Dict[str, float]:
        """Extracts Tax (PPN/PB1), Service Charge, and Discount amounts."""
        res = {"tax": 0.0, "service": 0.0, "discount": 0.0}

        for line in text_lines:
            line_upper = line.upper()
            matches = re.findall(r"(?:Rp\.?\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?|\d+)", line)
            if not matches:
                continue
            val = self.clean_number(matches[-1])

            if any(k in line_upper for k in ["PPN", "PB1", "PAJAK", "TAX", "GST"]):
                res["tax"] = max(res["tax"], val)
            elif any(k in line_upper for k in ["SERVICE", "SERVICE CHARGE", "BIAYA LAYANAN"]):
                res["service"] = max(res["service"], val)
            elif any(k in line_upper for k in ["DISCOUNT", "DISKON", "PROMO", "HEMAT", "VOUCHER"]):
                res["discount"] = max(res["discount"], val)

        return res

    def parse_line_items(self, text_lines: List[str]) -> List[Dict[str, Any]]:
        """Extracts itemized products and prices from receipt text."""
        items = []
        skip_keywords = [
            "TOTAL", "SUBTOTAL", "BAYAR", "TUNAI", "CASH", "KEMBALI", "CHANGE",
            "PPN", "PB1", "PAJAK", "TAX", "SERVICE", "DISKON", "PROMO", "STRUK",
            "NO.", "ITEM", "HARGA", "SELAMAT", "DATANG", "KASIR", "TANGGAL", "DATE"
        ]

        for line in text_lines:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 3:
                continue

            line_upper = line_clean.upper()
            if any(sk in line_upper for sk in skip_keywords):
                continue

            # Pattern: Item Name ... Qty x Price ... Subtotal OR Item Name ... Price
            # Matches line ending with amount
            match = re.search(r"^(.+?)\s+(?:(\d+)\s*[xX*]\s*)?(?:Rp\.?\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?|\d+)$", line_clean)
            if match:
                name, qty_str, price_str = match.groups()
                name_clean = name.strip()
                if len(name_clean) >= 2 and not name_clean.isdigit():
                    qty = float(qty_str) if qty_str else 1.0
                    total_price = self.clean_number(price_str)
                    unit_price = total_price / qty if qty > 0 else total_price

                    if 100 <= total_price <= 50000000:
                        items.append({
                            "item_name": name_clean.title(),
                            "qty": qty,
                            "price": unit_price,
                            "subtotal": total_price
                        })

        return items

    def parse_receipt(self, raw_text: str) -> Dict[str, Any]:
        """Full receipt parsing pipeline."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        merchant = self.parse_merchant(lines)
        trans_date = self.parse_date(raw_text)
        total_amount = self.parse_total(lines)
        additions = self.parse_tax_service_discount(lines)
        items = self.parse_line_items(lines)

        return {
            "merchant": merchant,
            "date": trans_date,
            "total_amount": total_amount,
            "tax_amount": additions["tax"],
            "service_charge": additions["service"],
            "discount_amount": additions["discount"],
            "items": items,
            "raw_text": raw_text
        }
