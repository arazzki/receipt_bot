import re
import datetime
import logging
from typing import Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from services.split_bill_engine import SplitBillEngine
from services.parser_service import ReceiptParser
from bot.utils.formatters import generate_split_bill_summary, format_rupiah, format_date, safe_html
from database.connection import get_db_session
from database.models import SplitBill, SplitBillItem, SplitBillParticipant, User

logger = logging.getLogger(__name__)

parser_service = ReceiptParser()

# State constants for conversation handler
SET_TITLE, SET_PARTICIPANTS, SET_ITEMS, SET_EXTRAS = range(4)

async def splitbill_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates interactive split bill creation or lists existing split bills."""
    context.user_data["splitbill_data"] = {
        "title": "Split Bill",
        "items": [],
        "participants": [],
        "assignments": {},
        "tax": 0.0,
        "service": 0.0,
        "discount": 0.0
    }

    keyboard = [
        [InlineKeyboardButton("➕ Buat Split Bill Baru", callback_data="sb_start_new")],
        [InlineKeyboardButton("📋 Lihat & Kelola Status Pelunasan", callback_data="sb_list_existing")]
    ]

    text = (
        "👥 <b>Kalkulator &amp; Pengelola Split Bill Engine</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih tindakan yang ingin Anda lakukan:"
    )

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    return SET_TITLE

async def sb_start_new_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Triggered when user clicks 'Buat Split Bill Baru'."""
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "👥 <b>Kalkulator Split Bill Engine</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Langkah 1/4: Silakan kirimkan <b>Judul Tagihan</b> atau Nama Tempat/Acara:\n"
        "<i>(Contoh: Makan Malam Solaria, Belanja Kontrakan)</i>"
    )
    await query.edit_message_text(text, parse_mode="HTML")
    return SET_TITLE

async def set_splitbill_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores title and asks for participants."""
    title = update.message.text.strip()
    sb_data = context.user_data.get("splitbill_data", {})
    sb_data["title"] = title
    context.user_data["splitbill_data"] = sb_data

    title_safe = safe_html(title)
    text = (
        f"✅ Judul Set: <b>{title_safe}</b>\n\n"
        "Langkah 2/4: Kirimkan <b>Daftar Nama Anggota</b> dipisahkan koma:\n"
        "<i>(Contoh: Budi, Andi, Citra, Dian)</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return SET_PARTICIPANTS

async def set_splitbill_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores participants and asks for items or calculates if items already populated from receipt scan."""
    raw_input = update.message.text.strip()
    names = [name.strip().title() for name in raw_input.split(",") if name.strip()]

    if not names:
        await update.message.reply_text("❌ Masukkan setidaknya 1 nama anggota (pisahkan dengan koma):")
        return SET_PARTICIPANTS

    sb_data = context.user_data.get("splitbill_data", {})
    sb_data["participants"] = names
    context.user_data["splitbill_data"] = sb_data

    names_safe = [safe_html(n) for n in names]

    if sb_data.get("items"):
        result = SplitBillEngine.calculate_split(
            items=sb_data["items"],
            participants=sb_data["participants"],
            assignments=sb_data.get("assignments", {}),
            tax_amount=sb_data.get("tax", 0.0),
            service_charge=sb_data.get("service", 0.0),
            discount_amount=sb_data.get("discount", 0.0)
        )
        sb_data["result"] = result
        context.user_data["splitbill_data"] = sb_data

        summary_text = generate_split_bill_summary(result, title=sb_data["title"])
        keyboard = [[InlineKeyboardButton("💾 Simpan ke Database", callback_data="save_splitbill_db")]]
        await update.message.reply_text(summary_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    text = (
        f"👥 <b>Anggota ({len(names)}):</b> {', '.join(names_safe)}\n\n"
        "Langkah 3/4: Kirimkan daftar <b>Item &amp; Harga</b> (satu item per baris):\n"
        "<i>(Contoh:\n"
        "Nasi Goreng 35000\n"
        "Es Teh Manis 8000\n"
        "Ayam Goreng 25000)</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return SET_ITEMS

async def set_splitbill_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores item breakdown using robust regex matching."""
    lines = [line.strip() for line in update.message.text.splitlines() if line.strip()]
    items = []

    for line in lines:
        match = re.search(r"^(.+?)(?:[-:]|\s+)?(?:Rp\.?\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?|\d+)$", line, re.IGNORECASE)
        if match:
            item_name, price_str = match.groups()
            item_name_clean = item_name.strip("-: ").title()
            price = parser_service.clean_number(price_str)
            if item_name_clean and price > 0:
                items.append({
                    "item_name": item_name_clean,
                    "qty": 1.0,
                    "price": price,
                    "subtotal": price
                })
        else:
            if len(line) >= 2:
                items.append({
                    "item_name": line.title(),
                    "qty": 1.0,
                    "price": 0.0,
                    "subtotal": 0.0
                })

    if not items:
        await update.message.reply_text(
            "❌ Format item tidak terdeteksi. Silakan kirim ulang format: <code>Nama Item Harga</code> (contoh: <code>Nasi Goreng 35000</code>):",
            parse_mode="HTML"
        )
        return SET_ITEMS

    sb_data = context.user_data.get("splitbill_data", {})
    sb_data["items"] = items
    context.user_data["splitbill_data"] = sb_data

    text = (
        f"🛒 <b>Total {len(items)} Item Berhasil Dicatat.</b>\n\n"
        "Langkah 4/4: Masukkan biaya tambahan format <code>Pajak, Service, Diskon</code> (atau <code>0</code> jika tidak ada):\n"
        "<i>(Contoh: <code>15000, 5000, 10000</code> atau <code>0</code>)</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return SET_EXTRAS

async def set_splitbill_extras(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses extras, performs calculation, and presents final result."""
    text_input = update.message.text.strip().lower()
    tax, service, discount = 0.0, 0.0, 0.0

    if text_input not in ["0", "tidak ada", "no", "skip", "-"]:
        try:
            parts = [parser_service.clean_number(p.strip()) for p in text_input.split(",")]
            if len(parts) >= 1: tax = parts[0]
            if len(parts) >= 2: service = parts[1]
            if len(parts) >= 3: discount = parts[2]
        except Exception:
            pass

    sb_data = context.user_data.get("splitbill_data", {})
    sb_data["tax"] = tax
    sb_data["service"] = service
    sb_data["discount"] = discount

    result = SplitBillEngine.calculate_split(
        items=sb_data["items"],
        participants=sb_data["participants"],
        assignments=sb_data.get("assignments", {}),
        tax_amount=tax,
        service_charge=service,
        discount_amount=discount
    )

    sb_data["result"] = result
    context.user_data["splitbill_data"] = sb_data

    summary_text = generate_split_bill_summary(result, title=sb_data["title"])
    keyboard = [[InlineKeyboardButton("💾 Simpan ke Database", callback_data="save_splitbill_db")]]

    await update.message.reply_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ConversationHandler.END

async def convert_receipt_to_splitbill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Converts active OCR scanned receipt into a Split Bill directly."""
    query = update.callback_query
    if query:
        await query.answer()

    receipt = context.user_data.get("active_receipt")
    if not receipt:
        await query.message.reply_text("❌ Data struk tidak ditemukan. Silakan pindai foto struk kembali.")
        return ConversationHandler.END

    sb_data = {
        "title": f"Split - {receipt.get('merchant', 'Struk')}",
        "items": receipt.get("items", []),
        "participants": [],
        "assignments": {},
        "tax": receipt.get("tax_amount", 0.0),
        "service": receipt.get("service_charge", 0.0),
        "discount": receipt.get("discount_amount", 0.0)
    }
    context.user_data["splitbill_data"] = sb_data

    title_safe = safe_html(sb_data['title'])
    text = (
        f"⚡ <b>KONVERSI STRUK KE SPLIT BILL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Judul: <b>{title_safe}</b>\n"
        f"Item Terimpor: <b>{len(sb_data['items'])} item</b>\n"
        f"Pajak: <code>{format_rupiah(sb_data['tax'])}</code> | Diskon: <code>{format_rupiah(sb_data['discount'])}</code>\n\n"
        f"Kirimkan <b>Daftar Nama Anggota</b> dipisahkan koma:\n"
        f"<i>(Contoh: Budi, Andi, Citra)</i>"
    )
    await query.message.reply_text(text, parse_mode="HTML")
    return SET_PARTICIPANTS

async def save_splitbill_db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Saves completed split bill to database."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    sb_data = context.user_data.get("splitbill_data", {})
    result = sb_data.get("result", {})
    if not result:
        await query.message.reply_text("❌ Data Split Bill tidak ditemukan atau telah kedaluwarsa.")
        return

    tg_user = query.from_user
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == tg_user.id).first()
        if not user:
            user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name)
            session.add(user)
            session.flush()

        split_bill = SplitBill(
            creator_id=tg_user.id,
            title=sb_data.get("title", "Split Bill"),
            total_amount=result.get("grand_total", 0.0),
            tax_amount=sb_data.get("tax", 0.0),
            service_charge=sb_data.get("service", 0.0),
            discount_amount=sb_data.get("discount", 0.0),
            status="ACTIVE"
        )
        session.add(split_bill)
        session.flush()

        for item in sb_data.get("items", []):
            sb_item = SplitBillItem(
                split_bill_id=split_bill.id,
                item_name=item.get("item_name", "Item"),
                qty=item.get("qty", 1.0),
                price=item.get("price", 0.0),
                subtotal=item.get("subtotal", 0.0)
            )
            session.add(sb_item)

        participants_res = result.get("participants", {})
        for name, p_data in participants_res.items():
            sb_p = SplitBillParticipant(
                split_bill_id=split_bill.id,
                participant_name=name,
                allocated_amount=p_data.get("final_amount", 0.0),
                is_paid=False
            )
            session.add(sb_p)

        session.commit()

        title_safe = safe_html(split_bill.title)
        success_text = (
            f"🎉 <b>SPLIT BILL BERHASIL DISIMPAN KE DATABASE MARIADB!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ID Split Bill: <code>#SB-{split_bill.id}</code>\n"
            f"Judul Tagihan: <b>{title_safe}</b>\n"
            f"Total Tagihan: <code>{format_rupiah(split_bill.total_amount)}</code>\n"
            f"Jumlah Anggota: <code>{len(participants_res)} orang</code>\n\n"
            f"💡 <i>Gunakan tombol di bawah untuk mengelola status pelunasan anggota.</i>"
        )
        keyboard = [
            [InlineKeyboardButton(f"📋 Kelola Pelunasan (#SB-{split_bill.id})", callback_data=f"sb_view_{split_bill.id}")],
            [InlineKeyboardButton("➕ Buat Split Bill Baru", callback_data="sb_start_new")]
        ]
        await query.edit_message_text(success_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data.pop("splitbill_data", None)

    except Exception as e:
        session.rollback()
        logger.error(f"Error saving split bill DB: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Gagal menyimpan split bill ke database: {e}")
    finally:
        session.close()

# --- LIST & EDIT PAYMENT SETTLEMENT STATUS ---

async def render_splitbill_detail(query: CallbackQuery, sb_id: int) -> None:
    """Helper to render split bill detail view cleanly."""
    session = get_db_session()
    try:
        sb = session.query(SplitBill).filter(SplitBill.id == sb_id).first()
        if not sb:
            await query.edit_message_text("❌ Split Bill tidak ditemukan di database.")
            return

        title_safe = safe_html(sb.title)
        grand_total = format_rupiah(sb.total_amount)
        created_str = format_date(sb.created_at)

        paid_count = sum(1 for p in sb.participants if p.is_paid)
        total_p = len(sb.participants)
        overall_status = "✅ LUNAS SEMUA" if paid_count == total_p and total_p > 0 else f"⏳ DALAM PROSES ({paid_count}/{total_p} Lunas)"

        text = f"💳 <b>DETAIL SPLIT BILL #SB-{sb.id}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>Judul:</b> <b>{title_safe}</b>\n"
        text += f"📅 <b>Tanggal:</b> <code>{created_str}</code>\n"
        text += f"💰 <b>Total Tagihan:</b> <code>{grand_total}</code>\n"
        text += f"📊 <b>Status Tagihan:</b> <b>{overall_status}</b>\n\n"
        text += f"👥 <b>DAFTAR ANGGOTA &amp; PELUNASAN:</b>\n"
        text += f"<i>(Klik tombol nama di bawah untuk mengubah status Lunas ↔ Belum)</i>\n\n"

        keyboard = []
        for p in sb.participants:
            p_name = safe_html(p.participant_name)
            p_amt = format_rupiah(p.allocated_amount)
            icon = "✅" if p.is_paid else "❌"
            status_text = "LUNAS" if p.is_paid else "BELUM"

            paid_at_str = f" (Bayar: {p.paid_at.strftime('%d/%m %H:%M')})" if p.is_paid and p.paid_at else ""
            text += f"• <b>{p_name}</b>: <code>{p_amt}</code> — {icon} <b>{status_text}</b>{paid_at_str}\n"

            btn_text = f"{icon} {p_name} ({p_amt}) -> Ubah ke {'Belum' if p.is_paid else 'Lunas'}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_p_{p.id}")])

        keyboard.append([InlineKeyboardButton("🔄 Refresh Status", callback_data=f"sb_view_{sb.id}")])
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Daftar Split Bill", callback_data="sb_list_existing")])

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()

async def list_user_splitbills_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists existing split bills from MariaDB database for status tracking."""
    query = update.callback_query
    if query:
        await query.answer()

    tg_user = update.effective_user
    session = get_db_session()
    try:
        split_bills = session.query(SplitBill).filter(
            SplitBill.creator_id == tg_user.id
        ).order_by(SplitBill.created_at.desc()).all()

        if not split_bills:
            text = "ℹ️ <b>Belum ada Split Bill yang tersimpan di database.</b>"
            keyboard = [[InlineKeyboardButton("➕ Buat Split Bill Baru", callback_data="sb_start_new")]]
            if query:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = "📋 <b>DAFTAR SPLIT BILL TERBARU</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nPilih tagihan di bawah untuk melihat rincian &amp; mengedit status pelunasan:"
        keyboard = []

        for sb in split_bills:
            paid_count = sum(1 for p in sb.participants if p.is_paid)
            total_p = len(sb.participants)
            status_icon = "✅ SELESAI" if sb.status == "SETTLED" or (total_p > 0 and paid_count == total_p) else f"{paid_count}/{total_p} Lunas"
            title_safe = safe_html(sb.title)
            btn_label = f"#SB-{sb.id}: {title_safe} ({format_rupiah(sb.total_amount)}) [{status_icon}]"
            keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"sb_view_{sb.id}")])

        keyboard.append([InlineKeyboardButton("➕ Buat Split Bill Baru", callback_data="sb_start_new")])

        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Error listing split bills: {e}", exc_info=True)
        if query:
            await query.message.reply_text(f"❌ Gagal memuat daftar split bill: {e}")
    finally:
        session.close()

async def view_splitbill_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows detailed view of a split bill with interactive toggle buttons for participant payment status."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    match = re.match(r"^sb_view_(\d+)$", query.data)
    if match:
        await render_splitbill_detail(query, int(match.group(1)))

async def toggle_participant_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggles participant payment status (is_paid: True ↔ False) in MariaDB."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    match = re.match(r"^toggle_p_(\d+)$", query.data)
    if not match:
        return

    p_id = int(match.group(1))
    session = get_db_session()
    sb_id = None

    try:
        participant = session.query(SplitBillParticipant).filter(SplitBillParticipant.id == p_id).first()
        if not participant:
            await query.message.reply_text("❌ Data anggota tidak ditemukan.")
            return

        sb_id = participant.split_bill_id

        # Toggle is_paid
        participant.is_paid = not participant.is_paid
        participant.paid_at = datetime.datetime.now() if participant.is_paid else None

        session.flush()

        # Update SplitBill status if all participants paid
        sb = session.query(SplitBill).filter(SplitBill.id == sb_id).first()
        if sb:
            all_paid = all(p.is_paid for p in sb.participants)
            sb.status = "SETTLED" if all_paid else "ACTIVE"

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error toggling participant status: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Gagal mengubah status pelunasan: {e}")
        return
    finally:
        session.close()

    # Re-render detail view directly without mutating read-only CallbackQuery.data!
    if sb_id:
        await render_splitbill_detail(query, sb_id)

async def cancel_splitbill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels conversation flow."""
    await update.message.reply_text("🚫 Proses Split Bill dibatalkan.")
    context.user_data.pop("splitbill_data", None)
    return ConversationHandler.END
