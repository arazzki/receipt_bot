import html
import datetime
from typing import Dict, Any

def safe_html(text: Any) -> str:
    """Escapes HTML special characters in dynamic user text to prevent Telegram entity errors."""
    if text is None:
        return ""
    return html.escape(str(text))

def format_rupiah(amount: float) -> str:
    """Formats numeric amount into Rupiah format: Rp 150.000"""
    try:
        val = float(amount)
        formatted = f"{val:,.0f}".replace(",", ".")
        return f"Rp {formatted}"
    except (ValueError, TypeError):
        return "Rp 0"

def format_date(dt: Any) -> str:
    """Formats date to DD-MM-YYYY string."""
    if isinstance(dt, (datetime.date, datetime.datetime)):
        return dt.strftime("%d-%m-%Y")
    return str(dt)

def generate_receipt_summary(data: Dict[str, Any]) -> str:
    """Generates formatted HTML summary of parsed receipt."""
    merchant = safe_html(data.get("merchant", "Merchant Tidak Diketahui"))
    trans_date = format_date(data.get("date", datetime.date.today()))
    total = format_rupiah(data.get("total_amount", 0.0))
    tax = data.get("tax_amount", 0.0)
    service = data.get("service_charge", 0.0)
    discount = data.get("discount_amount", 0.0)
    items = data.get("items", [])

    text = f"🧾 <b>DRAFT HASIL EKSTRAKSI STRUK</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏪 <b>Toko/Merchant:</b> <code>{merchant}</code>\n"
    text += f"📅 <b>Tanggal:</b> <code>{trans_date}</code>\n"
    text += f"💰 <b>Total Belanja:</b> <code>{total}</code>\n"

    if tax > 0 or service > 0 or discount > 0:
        text += f"\n📌 <b>Rincian Tambahan:</b>\n"
        if tax > 0:
            text += f"• PPN / Pajak: <code>{format_rupiah(tax)}</code>\n"
        if service > 0:
            text += f"• Service Charge: <code>{format_rupiah(service)}</code>\n"
        if discount > 0:
            text += f"• Diskon Promo: <code>-{format_rupiah(discount)}</code>\n"

    if items:
        text += f"\n🛒 <b>Item Terdeteksi ({len(items)}):</b>\n"
        for idx, item in enumerate(items[:10], 1):
            name = safe_html(item.get("item_name", "Item"))
            subtotal = format_rupiah(item.get("subtotal", 0.0))
            qty = item.get("qty", 1)
            text += f"{idx}. {name} (x{qty}) - <code>{subtotal}</code>\n"
        if len(items) > 10:
            text += f" <i>...dan {len(items)-10} item lainnya.</i>\n"

    text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💡 <i>Silakan konfirmasi atau sesuaikan data di atas menggunakan tombol di bawah ini.</i>"
    return text

def generate_split_bill_summary(result: Dict[str, Any], title: str = "Split Bill") -> str:
    """Generates clean HTML breakdown of split bill settlement."""
    grand_total = format_rupiah(result.get("grand_total", 0.0))
    participants = result.get("participants", {})

    title_safe = safe_html(title)
    text = f"👥 <b>RANGKUMAN SPLIT BILL: {title_safe.upper()}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💳 <b>Total Tagihan:</b> <code>{grand_total}</code>\n\n"
    text += f"📊 <b>RINCIAN PER ANGGOTA:</b>\n"

    for name, p_data in participants.items():
        name_safe = safe_html(name)
        p_final = format_rupiah(p_data.get("final_amount", 0.0))
        p_sub = format_rupiah(p_data.get("items_subtotal", 0.0))
        p_tax = p_data.get("tax_share", 0.0)
        p_svc = p_data.get("service_share", 0.0)
        p_disc = p_data.get("discount_share", 0.0)

        text += f"\n👤 <b>{name_safe.upper()}</b>\n"
        text += f"   • Subtotal Item: <code>{p_sub}</code>\n"
        if p_tax > 0 or p_svc > 0 or p_disc > 0:
            extras = []
            if p_tax > 0: extras.append(f"Pajak: {format_rupiah(p_tax)}")
            if p_svc > 0: extras.append(f"Svc: {format_rupiah(p_svc)}")
            if p_disc > 0: extras.append(f"Disc: -{format_rupiah(p_disc)}")
            text += f"   • Biaya Tambahan: <code>({', '.join(extras)})</code>\n"
        text += f"   👉 <b>Total Wajib Bayar: {p_final}</b>\n"

    text += f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"✅ <i>Gunakan tombol di bawah untuk menyimpan ke database.</i>"
    return text
