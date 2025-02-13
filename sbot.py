import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Dein Bot-Token (Test-Token, wie gewünscht eingesetzt)
BOT_TOKEN = "7720861006:AAGbTV0_haSgPhtNsv2unqy6ZiyI7A_BrBU"

# Logging aktivieren
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def delete_system_messages(update: Update, context: CallbackContext):
    """Löscht neue Systemnachrichten automatisch."""
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member or update.message.pinned_message:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            logging.info(f"✅ Systemnachricht gelöscht in Chat {update.message.chat_id}")

async def run_bot():
    """Startet den Telegram-Bot als asynchronen Task, um asyncio-Fehler zu vermeiden."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Überwacht Systemnachrichten und löscht sie
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_system_messages))

    logging.info("🚀 Bot läuft und löscht neue Systemnachrichten...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logging.warning("⚠️ Event loop läuft bereits, starte Bot als Task...")
            task = loop.create_task(run_bot())
        else:
            logging.info("🚀 Starte Bot in neuer Event Loop...")
            loop.run_until_complete(run_bot())
    except RuntimeError:
        logging.info("🔄 Erstelle neue Event Loop für den Bot...")
        asyncio.run(run_bot())