import os
import datetime
import logging
from pathlib import Path
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import get_db_session
from database.models import Transaction, TransactionItem
from bot.utils.formatters import format_rupiah, format_date, safe_html
from config import TEMP_DIR

logger = logging.getLogger(__name__)

async def rekap_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /rekap command and presents timeframe options."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Hari Ini", callback_data="rekap_period_today"),
            InlineKeyboardButton("🗓️ Minggu Ini", callback_data="rekap_period_week")
        ],
        [
            InlineKeyboardButton("📊 Bulan Ini", callback_data="rekap_period_month"),
            InlineKeyboardButton("📈 Semua Waktu", callback_data="rekap_period_all")
        ],
        [
            InlineKeyboardButton("📥 Ekspor File (Excel / CSV)", callback_data="rekap_export_menu")
        ]
    ]

    text = (
        "📊 <b>REKAPITULASI PENGELUARAN</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih periode rekapitulasi keuangan yang ingin Anda lihat:"
    )

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_rekap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles timeframe filtering and file export for recap."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data
    tg_user = query.from_user
    session = get_db_session()

    try:
        today = datetime.date.today()
        start_date = None
        period_name = "Semua Waktu"

        if data == "rekap_period_today":
            start_date = today
            period_name = "Hari Ini"
        elif data == "rekap_period_week":
            start_date = today - datetime.timedelta(days=7)
            period_name = "7 Hari Terakhir"
        elif data == "rekap_period_month":
            start_date = today.replace(day=1)
            period_name = f"Bulan {today.strftime('%B %Y')}"
        elif data == "rekap_period_all":
            start_date = None
            period_name = "Semua Waktu"

        if data.startswith("rekap_period_"):
            q = session.query(Transaction).filter(Transaction.user_id == tg_user.id)
            if start_date:
                q = q.filter(Transaction.transaction_date >= start_date)

            transactions = q.order_by(Transaction.transaction_date.desc()).all()

            period_safe = safe_html(period_name)
            if not transactions:
                await query.edit_message_text(
                    f"ℹ️ Belum ada pengeluaran yang dicatat untuk periode <b>{period_safe}</b>.",
                    parse_mode="HTML"
                )
                return

            total_spent = sum(t.total_amount for t in transactions)

            cat_totals = {}
            for t in transactions:
                cat = t.category or "Lain-lain"
                cat_totals[cat] = cat_totals.get(cat, 0.0) + float(t.total_amount)

            text = f"📊 <b>REKAPITULASI PENGELUARAN ({period_safe.upper()})</b>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"💰 <b>Total Pengeluaran:</b> <code>{format_rupiah(total_spent)}</code> ({len(transactions)} transaksi)\n\n"
            text += f"🏷️ <b>Rincian Per Kategori:</b>\n"
            for cat, amount in cat_totals.items():
                pct = (amount / total_spent * 100) if total_spent > 0 else 0
                cat_safe = safe_html(cat)
                text += f"• {cat_safe}: <code>{format_rupiah(amount)}</code> ({pct:.1f}%)\n"

            text += f"\n📝 <b>5 Transaksi Terakhir:</b>\n"
            for t in transactions[:5]:
                m_safe = safe_html(t.merchant)
                text += f"• {format_date(t.transaction_date)} | {m_safe} | <code>{format_rupiah(t.total_amount)}</code>\n"

            keyboard = [
                [InlineKeyboardButton("📥 Ekspor ke Excel (.xlsx)", callback_data="export_excel")],
                [InlineKeyboardButton("📥 Ekspor ke CSV (.csv)", callback_data="export_csv")],
                [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_rekap")]
            ]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "export_excel" or data == "export_csv":
            q = session.query(Transaction).filter(Transaction.user_id == tg_user.id).order_by(Transaction.transaction_date.desc())
            transactions = q.all()

            if not transactions:
                await query.message.reply_text("ℹ️ Tidak ada data untuk diekspor.")
                return

            export_data = []
            for t in transactions:
                export_data.append({
                    "ID Transaksi": t.id,
                    "Tanggal": format_date(t.transaction_date),
                    "Merchant / Toko": t.merchant,
                    "Total (Rp)": float(t.total_amount),
                    "Kategori": t.category,
                    "Tanggal Dibuat": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
                })

            df = pd.DataFrame(export_data)

            if data == "export_excel":
                file_path = TEMP_DIR / f"Rekap_Pengeluaran_{tg_user.id}.xlsx"
                df.to_excel(file_path, index=False, engine="openpyxl")
                await query.message.reply_document(
                    document=open(file_path, "rb"),
                    filename=f"Rekap_Pengeluaran_{today.strftime('%Y%m%d')}.xlsx",
                    caption="📊 <b>Berikut berkas Laporan Rekapitulasi Pengeluaran Excel Anda.</b>",
                    parse_mode="HTML"
                )
            else:
                file_path = TEMP_DIR / f"Rekap_Pengeluaran_{tg_user.id}.csv"
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
                await query.message.reply_document(
                    document=open(file_path, "rb"),
                    filename=f"Rekap_Pengeluaran_{today.strftime('%Y%m%d')}.csv",
                    caption="📊 <b>Berikut berkas Laporan Rekapitulasi Pengeluaran CSV Anda.</b>",
                    parse_mode="HTML"
                )

    except Exception as e:
        logger.error(f"Error in rekap callback: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Terjadi kesalahan saat memproses rekapitulasi: {e}")
    finally:
        session.close()
