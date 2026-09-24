import os
import uuid
import datetime
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import TEMP_DIR
from services.ocr_engine import OCREngine
from services.parser_service import ReceiptParser
from bot.utils.formatters import generate_receipt_summary, format_rupiah, format_date, safe_html
from database.connection import get_db_session
from database.models import Transaction, TransactionItem, User

logger = logging.getLogger(__name__)

ocr_engine = OCREngine()
parser_service = ReceiptParser()

# Categories available
CATEGORIES = [
    "Makanan & Minuman", "Minimarket / Groceries", "Belanja & Fashion",
    "Transportasi", "Hiburan", "Tagihan & Utilitas", "Lain-lain"
]

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receives receipt photo, triggers OCR pipeline, and presents extracted draft."""
    message = update.message
    if not message or not message.photo:
        return

    # Send processing status message
    status_msg = await message.reply_text("🔎 <b>Memproses citra struk via OCR &amp; Computer Vision...</b>", parse_mode="HTML")

    try:
        # Download highest resolution photo
        photo = message.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)
        
        file_path = TEMP_DIR / f"receipt_{uuid.uuid4().hex[:8]}.jpg"
        await file_obj.download_to_drive(file_path)

        # Run OCR
        raw_text = ocr_engine.extract_text(str(file_path), preprocess=True)
        parsed_data = parser_service.parse_receipt(raw_text)
        parsed_data["image_path"] = str(file_path)
        parsed_data["category"] = "Makanan & Minuman" if "STARBUCKS" in parsed_data["merchant"].upper() or "RESTO" in parsed_data["merchant"].upper() else "Minimarket / Groceries"

        # Save to context session
        context.user_data["active_receipt"] = parsed_data

        # Build inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✏️ Edit Toko", callback_data="edit_receipt_merchant"),
                InlineKeyboardButton("📅 Edit Tanggal", callback_data="edit_receipt_date")
            ],
            [
                InlineKeyboardButton("💰 Edit Total", callback_data="edit_receipt_total"),
                InlineKeyboardButton("🏷️ Pilih Kategori", callback_data="edit_receipt_category")
            ],
            [
                InlineKeyboardButton("💾 Simpan Pengeluaran", callback_data="save_receipt_db")
            ],
            [
                InlineKeyboardButton("👥 Jadikan Split Bill", callback_data="convert_to_splitbill")
            ]
        ]

        summary_text = generate_receipt_summary(parsed_data)
        await status_msg.edit_text(summary_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Error processing receipt photo: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Gagal memproses gambar struk.</b>\nDetail Kesalahan: <code>{safe_html(str(e))}</code>",
            parse_mode="HTML"
        )

async def handle_receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline button clicks for receipt editing and saving."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = query.data
    receipt = context.user_data.get("active_receipt")

    if not receipt and data.startswith("edit_receipt_"):
        await query.message.reply_text("❌ Session receipt telah kedaluwarsa. Silakan kirimkan foto struk kembali.")
        return

    if data == "edit_receipt_category":
        keyboard = [
            [InlineKeyboardButton(cat, callback_data=f"set_cat_{idx}")]
            for idx, cat in enumerate(CATEGORIES)
        ]
        cat_safe = safe_html(receipt.get('category', 'Lain-lain'))
        await query.edit_message_text(
            f"🏷️ <b>Pilih Kategori Pengeluaran:</b>\nStatus Saat Ini: <code>{cat_safe}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("set_cat_"):
        cat_idx = int(data.split("_")[-1])
        selected_cat = CATEGORIES[cat_idx]
        receipt["category"] = selected_cat
        context.user_data["active_receipt"] = receipt

        # Refresh summary
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Toko", callback_data="edit_receipt_merchant"), InlineKeyboardButton("📅 Edit Tanggal", callback_data="edit_receipt_date")],
            [InlineKeyboardButton("💰 Edit Total", callback_data="edit_receipt_total"), InlineKeyboardButton("🏷️ Pilih Kategori", callback_data="edit_receipt_category")],
            [InlineKeyboardButton("💾 Simpan Pengeluaran", callback_data="save_receipt_db")],
            [InlineKeyboardButton("👥 Jadikan Split Bill", callback_data="convert_to_splitbill")]
        ]
        await query.edit_message_text(
            generate_receipt_summary(receipt),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "save_receipt_db":
        tg_user = query.from_user
        session = get_db_session()
        try:
            user = session.query(User).filter(User.id == tg_user.id).first()
            if not user:
                user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name)
                session.add(user)
                session.flush()

            transaction = Transaction(
                user_id=tg_user.id,
                merchant=receipt.get("merchant", "Struk Belanja"),
                transaction_date=receipt.get("date", datetime.date.today()),
                total_amount=receipt.get("total_amount", 0.0),
                category=receipt.get("category", "Lain-lain"),
                raw_ocr_text=receipt.get("raw_text", ""),
                image_path=receipt.get("image_path", "")
            )
            session.add(transaction)
            session.flush()

            for item in receipt.get("items", []):
                t_item = TransactionItem(
                    transaction_id=transaction.id,
                    item_name=item.get("item_name", "Item"),
                    qty=item.get("qty", 1.0),
                    price=item.get("price", 0.0),
                    subtotal=item.get("subtotal", 0.0)
                )
                session.add(t_item)

            session.commit()

            m_safe = safe_html(transaction.merchant)
            cat_safe = safe_html(transaction.category)
            success_text = (
                f"✅ <b>PENGELUARAN BERHASIL DISIMPAN!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏪 <b>Toko/Merchant:</b> <code>{m_safe}</code>\n"
                f"📅 <b>Tanggal:</b> <code>{format_date(transaction.transaction_date)}</code>\n"
                f"💰 <b>Total:</b> <code>{format_rupiah(transaction.total_amount)}</code>\n"
                f"🏷️ <b>Kategori:</b> <code>{cat_safe}</code>\n\n"
                f"Gunakan perintah /rekap untuk melihat statistik pengeluaran Anda."
            )
            await query.edit_message_text(success_text, parse_mode="HTML")
            context.user_data.pop("active_receipt", None)

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving transaction to DB: {e}")
            await query.message.reply_text(f"❌ Gagal menyimpan ke basis data: {e}")
        finally:
            session.close()

    elif data == "edit_receipt_merchant":
        context.user_data["editing_field"] = "merchant"
        await query.message.reply_text("✏️ Silakan balaskan teks nama Toko/Merchant yang baru:")

    elif data == "edit_receipt_total":
        context.user_data["editing_field"] = "total"
        await query.message.reply_text("💰 Silakan balaskan nominal Total yang baru (contoh: 150000):")

    elif data == "edit_receipt_date":
        context.user_data["editing_field"] = "date"
        await query.message.reply_text("📅 Silakan balaskan Tanggal baru format YYYY-MM-DD (contoh: 2026-09-24):")

async def handle_edit_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text input when user is editing merchant/total/date manually."""
    editing_field = context.user_data.get("editing_field")
    receipt = context.user_data.get("active_receipt")

    if not editing_field or not receipt or not update.message:
        return

    text_input = update.message.text.strip()

    if editing_field == "merchant":
        receipt["merchant"] = text_input.title()
        m_safe = safe_html(receipt['merchant'])
        await update.message.reply_text(f"✅ Toko diperbarui menjadi: <code>{m_safe}</code>", parse_mode="HTML")
    elif editing_field == "total":
        val = parser_service.clean_number(text_input)
        receipt["total_amount"] = val
        await update.message.reply_text(f"✅ Total diperbarui menjadi: <code>{format_rupiah(val)}</code>", parse_mode="HTML")
    elif editing_field == "date":
        new_date = parser_service.parse_date(text_input)
        receipt["date"] = new_date
        await update.message.reply_text(f"✅ Tanggal diperbarui menjadi: <code>{format_date(new_date)}</code>", parse_mode="HTML")

    context.user_data.pop("editing_field", None)
    context.user_data["active_receipt"] = receipt

    # Show updated draft
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Toko", callback_data="edit_receipt_merchant"), InlineKeyboardButton("📅 Edit Tanggal", callback_data="edit_receipt_date")],
        [InlineKeyboardButton("💰 Edit Total", callback_data="edit_receipt_total"), InlineKeyboardButton("🏷️ Pilih Kategori", callback_data="edit_receipt_category")],
        [InlineKeyboardButton("💾 Simpan Pengeluaran", callback_data="save_receipt_db")],
        [InlineKeyboardButton("👥 Jadikan Split Bill", callback_data="convert_to_splitbill")]
    ]
    await update.message.reply_text(
        generate_receipt_summary(receipt),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
