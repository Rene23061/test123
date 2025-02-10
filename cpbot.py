import logging
import asyncio
from telegram.ext import Application, MessageHandler, filters

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logging.info("Bot wird gestartet...")

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Nachricht bearbeiten ---
async def handle_message(update, context):
    message = update.message.text
    username = update.message.from_user.username if update.message.from_user else "Unbekannt"
    chat_id = update.message.chat_id

    logging.info(f"Nachricht empfangen von @{username} in Chat {chat_id}: {message}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    application = Application.builder().token(TOKEN).build()

    # Alle Nachrichten aus allen Gruppen (inkl. Themen) abfangen
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUP, handle_message))

    # Bot starten
    await application.initialize()
    await application.start()
    logging.info("Bot läuft... Drücke STRG+C zum Beenden.")

    # Warten auf STRG+C
    try:
        await asyncio.Future()  # Unendliches Warten
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende den Bot...")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())