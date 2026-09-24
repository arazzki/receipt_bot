import datetime
import pytest
from services.parser_service import ReceiptParser

@pytest.fixture
def parser():
    return ReceiptParser()

def test_clean_number(parser):
    assert parser.clean_number("Rp 150.000") == 150000.0
    assert parser.clean_number("150.000,00") == 150000.0
    assert parser.clean_number("Rp150,000.00") == 150000.0
    assert parser.clean_number("50000") == 50000.0
    assert parser.clean_number("INVALID") == 0.0

def test_parse_merchant(parser):
    lines1 = ["INDOMARET POINT", "JL. KEMANG RAYA", "TELP. 021-12345"]
    assert parser.parse_merchant(lines1) == "Indomaret"

    lines2 = ["STARBUCKS COFFEE", "RESERVE KEMANG", "TOTAL: 85.000"]
    assert parser.parse_merchant(lines2) == "Starbucks"

    lines3 = ["SOLARIA RESTORAN", "MALL KELAPA GADING", "24/09/2026"]
    assert parser.parse_merchant(lines3) == "Solaria"

def test_parse_date(parser):
    text1 = "STRUK BELANJA\nTANGGAL: 24/09/2026\nTOTAL: 50.000"
    assert parser.parse_date(text1) == datetime.date(2026, 9, 24)

    text2 = "INDOMARET\n24 Sep 2026 14:30\nTOTAL: 35.000"
    assert parser.parse_date(text2) == datetime.date(2026, 9, 24)

    text3 = "STARBUCKS\n2026-09-24 10:15:00"
    assert parser.parse_date(text3) == datetime.date(2026, 9, 24)

def test_parse_total(parser):
    lines1 = [
        "INDOMARET",
        "ROTI MANIS   10.000",
        "SUSU KOTAK   15.000",
        "SUBTOTAL     25.000",
        "GRAND TOTAL  25.000",
        "TUNAI        50.000",
        "KEMBALI      25.000"
    ]
    assert parser.parse_total(lines1) == 25000.0

    lines2 = [
        "SOLARIA RESTO",
        "NASI GORENG  35.000",
        "ES TEH       10.000",
        "TOTAL BAYAR  45.000"
    ]
    assert parser.parse_total(lines2) == 45000.0

def test_parse_tax_and_discount(parser):
    lines = [
        "SUBTOTAL     100.000",
        "PPN 10%       10.000",
        "SERVICE CHARGE 5.000",
        "DISKON PROMO  -15.000",
        "GRAND TOTAL  100.000"
    ]
    extras = parser.parse_tax_service_discount(lines)
    assert extras["tax"] == 10000.0
    assert extras["service"] == 5000.0
    assert extras["discount"] == 15000.0

def test_parse_full_receipt(parser):
    raw_ocr = """
    INDOMARET HYBRID KEMANG
    JL. KEMANG RAYA NO. 12
    TANGGAL: 24/09/2026
    
    AIR MINERAL 600ML 1x 5.000
    SNACK CHITATO    1x 12.000
    COCA COLA 330ML  1x 8.000
    
    SUBTOTAL         25.000
    DISKON PROMO      3.000
    TOTAL BAYAR      22.000
    CASH             50.000
    KEMBALI          28.000
    """
    res = parser.parse_receipt(raw_ocr)
    assert res["merchant"] == "Indomaret"
    assert res["date"] == datetime.date(2026, 9, 24)
    assert res["total_amount"] == 22000.0
    assert res["discount_amount"] == 3000.0
    assert len(res["items"]) >= 2
