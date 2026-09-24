import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import get_db_session
from database.models import User
from bot.utils.formatters import safe_html

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command, registers user in MariaDB/SQLite DB."""
    tg_user = update.effective_user
    if not tg_user:
        return

    # Register user in DB
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == tg_user.id).first()
        if not user:
            user = User(
                id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name
            )
            session.add(user)
            session.commit()
            logger.info(f"New user registered: {tg_user.id} ({tg_user.username})")
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error registering user: {e}")
    finally:
        session.close()

    fname_safe = safe_html(tg_user.first_name)
    welcome_text = (
        f"👋 <b>Selamat Datang, {fname_safe}!</b>\n\n"
        f"🤖 <b>ReceiptBot</b> adalah asisten otomatisasi pencatatan keuangan &amp; kalkulasi <b>Split Bill</b> grup.\n\n"
        f"📌 <b>Fitur Utama:</b>\n"
        f"📸 <b>Pindai Struk:</b> Kirimkan foto struk belanja untuk otomatisasi entri OCR instan.\n"
        f"👥 <b>Split Bill Engine:</b> Bagi tagihan multi-item beserta pajak &amp; diskon secara akurat.\n"
        f"📊 <b>Rekapitulasi:</b> Pantau statistik pengeluaran dan ekspor laporan ke Excel/CSV.\n\n"
        f"💡 <b>Petunjuk Penggunaan:</b>\n"
        f"• <b>Kirim Foto Struk</b> langsung ke chat ini untuk memindai.\n"
        f"• Perintah <code>/splitbill</code> - Mulai kalkulasi bagi tagihan grup.\n"
        f"• Perintah <code>/rekap</code> - Lihat rekapitulasi pengeluaran bulanan.\n"
        f"• Perintah <code>/help</code> - Bantuan lengkap."
    )

    keyboard = [
        [
            InlineKeyboardButton("📊 Lihat Rekapitulasi", callback_data="menu_rekap"),
            InlineKeyboardButton("👥 Split Bill", callback_data="menu_splitbill")
        ],
        [
            InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")
        ]
    ]

    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /help command."""
    help_text = (
        "📖 <b>PANDUAN LENGKAP RECEIPTBOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Pindai Struk Otomatis (OCR):</b>\n"
        "• Ambil foto struk belanja dengan pencahayaan cukup dan orientasi tegak.\n"
        "• Kirimkan foto ke chat bot ini.\n"
        "• Bot akan mengekstrak Toko, Tanggal, Nominal Total, &amp; Rincian Item.\n"
        "• Anda dapat mengkonfirmasi atau merubah draf sebelum disimpan.\n\n"
        "2️⃣ <b>Fitur Split Bill Grup (<code>/splitbill</code>):</b>\n"
        "• Digunakan saat makan bersama atau belanja kelompok.\n"
        "• Masukkan rincian harga per item dan nama anggota.\n"
        "• Bot akan menghitung persentase proporsional PPN/Pajak, Service Charge, dan Diskon secara adil.\n\n"
        "3️⃣ <b>Rekapitulasi Pengeluaran (<code>/rekap</code>):</b>\n"
        "• Filter statistik pengeluaran (Hari Ini, Minggu Ini, Bulan Ini).\n"
        "• Ekspor berkas laporan format Excel (.xlsx) atau CSV."
    )

    if update.message:
        await update.message.reply_text(help_text, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(help_text, parse_mode="HTML")
