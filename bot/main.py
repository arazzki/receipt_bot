import sys
import logging
from pathlib import Path

# Ensure root dir in python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from telegram import Update, BotCommand
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from config import TELEGRAM_BOT_TOKEN
from database.connection import init_db
from bot.handlers.start_handler import start_command, help_command
from bot.handlers.receipt_handler import (
    handle_receipt_photo, handle_receipt_callback, handle_edit_text_input
)
from bot.handlers.splitbill_handler import (
    splitbill_command, sb_start_new_callback, list_user_splitbills_callback,
    view_splitbill_detail_callback, toggle_participant_paid_callback,
    set_splitbill_title, set_splitbill_participants,
    set_splitbill_items, set_splitbill_extras, convert_receipt_to_splitbill,
    save_splitbill_db_callback, cancel_splitbill,
    SET_TITLE, SET_PARTICIPANTS, SET_ITEMS, SET_EXTRAS
)
from bot.handlers.rekap_handler import rekap_command, handle_rekap_callback

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exceptions caused by updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>Terjadi kesalahan internal pada sistem bot.</b>\nTim pengembang telah diberitahu.",
            parse_mode="HTML"
        )

async def post_init(application: Application) -> None:
    """Set the bot's commands menu on startup."""
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("help", "Bantuan & panduan penggunaan"),
        BotCommand("rekap", "Ringkasan pengeluaran & export"),
        BotCommand("splitbill", "Bagi tagihan grup"),
        BotCommand("history", "Riwayat & pelunasan tagihan")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands successfully registered!")

def main() -> None:
    """Starts the ReceiptBot application."""
    logger.info("Initializing ReceiptBot database...")
    init_db()

    if not TELEGRAM_BOT_TOKEN or "ExampleToken" in TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured or using example token in .env!")
        print("\n========================================================")
        print("⚠️ WARNING: TELEGRAM_BOT_TOKEN is not configured in .env")
        print("Please edit .env and insert your real Telegram Bot Token.")
        print("========================================================\n")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Split bill conversation handler with allow_reentry=True
    splitbill_conv = ConversationHandler(
        entry_points=[
            CommandHandler("splitbill", splitbill_command),
            CallbackQueryHandler(sb_start_new_callback, pattern="^sb_start_new$"),
            CallbackQueryHandler(splitbill_command, pattern="^menu_splitbill$"),
            CallbackQueryHandler(convert_receipt_to_splitbill, pattern="^convert_to_splitbill$")
        ],
        states={
            SET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_splitbill_title)],
            SET_PARTICIPANTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_splitbill_participants)],
            SET_ITEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_splitbill_items)],
            SET_EXTRAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_splitbill_extras)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_splitbill),
            CommandHandler("splitbill", splitbill_command)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        per_message=False
    )

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rekap", rekap_command))
    app.add_handler(CommandHandler("summary", rekap_command))
    app.add_handler(CommandHandler("history", list_user_splitbills_callback))
    app.add_handler(splitbill_conv)

    # Split bill management callback query handlers
    app.add_handler(CallbackQueryHandler(list_user_splitbills_callback, pattern="^sb_list_existing$"))
    app.add_handler(CallbackQueryHandler(view_splitbill_detail_callback, pattern="^sb_view_\\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_participant_paid_callback, pattern="^toggle_p_\\d+$"))
    app.add_handler(CallbackQueryHandler(save_splitbill_db_callback, pattern="^save_splitbill_db$"))

    # General Callback Query handlers
    app.add_handler(CallbackQueryHandler(help_command, pattern="^menu_help$"))
    app.add_handler(CallbackQueryHandler(rekap_command, pattern="^menu_rekap$"))
    app.add_handler(CallbackQueryHandler(handle_rekap_callback, pattern="^(rekap_|export_)"))
    app.add_handler(CallbackQueryHandler(handle_receipt_callback))

    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_text_input))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("ReceiptBot is starting long polling loop...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
