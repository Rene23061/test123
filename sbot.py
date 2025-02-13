import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext

# Dein Bot-Token (Test-Token wie gewünscht)
BOT_TOKEN = "7720861006:AAGbTV0_haSgPhtNsv2unqy6ZiyI7A_BrBU"

# Logging für Debugging (optional, aber nützlich)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def delete_system_messages(update: Update, context: CallbackContext):
    """Löscht neue Systemnachrichten automatisch."""
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member or update.message.pinned_message:
            await update.message.delete()
            logging.info(f"✅ Systemnachricht gelöscht in Chat {update.message.chat_id}")

def main():
    """Startet den Telegram-Bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Systemnachrichten überwachen und löschen
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_system_messages))

    logging.info("🚀 Bot läuft und löscht neue Systemnachrichten...")
    app.run_polling()

if __name__ == "__main__":
    main()