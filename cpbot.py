import logging
import asyncio
from telegram.ext import Application, MessageHandler, filters

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Auf INFO setzen, damit alle wichtigen Schritte angezeigt werden
)
logging.getLogger("telegram").setLevel(logging.DEBUG)  # Telegram-spezifisches Debugging

logging.info("Bot wird gestartet...")

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Nachricht behandeln ---
async def handle_message(update, context):
    message = update.message.text
    username = update.message.from_user.username if update.message.from_user else "Unbekannt"
    chat_id = update.message.chat_id

    logging.info(f"Nachricht empfangen von @{username} in Chat {chat_id}: {message}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    logging.info("Initialisiere die Anwendung...")
    application = Application.builder().token(TOKEN).build()

    logging.info("Füge Nachrichten-Handler hinzu...")
    # Alle Nachrichten abfangen
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    logging.info("Starte den Bot...")
    await application.initialize()
    await application.start()
    logging.info("Bot läuft... Drücke STRG+C zum Beenden.")

    # Warten, bis STRG+C gedrückt wird
    try:
        await asyncio.Event().wait()  # Wartet unendlich
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende den Bot...")
    finally:
        await application.stop()
        await application.shutdown()
        logging.info("Bot wurde erfolgreich beendet.")

if __name__ == '__main__':
    asyncio.run(main())