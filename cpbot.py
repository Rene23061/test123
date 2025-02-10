import logging
import asyncio
from telegram.ext import Application, MessageHandler, filters

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("telegram").setLevel(logging.DEBUG)

logging.info("Bot wird gestartet...")

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Funktion zum Abrufen von Gruppen- und Themen-Infos ---
async def fetch_group_info(application: Application):
    logging.info("Abrufen der Gruppeninformationen...")

    # Beispiel: ID der Gruppe, mit der du testen willst (später automatisierbar)
    # Die ID sollte durch vorherige Tests bekannt sein oder dynamisch geholt werden
    chat_id = -1001234567890  # Beispiel-Chat-ID (Supergruppe)

    try:
        chat = await application.bot.get_chat(chat_id)
        logging.info(f"Erfolgreich verbunden mit der Gruppe: {chat.title} (ID: {chat.id})")

        # Prüfen, ob die Gruppe Themen unterstützt (Supergruppen)
        if chat.is_forum:
            logging.info(f"Die Gruppe '{chat.title}' hat Themen aktiviert.")
        else:
            logging.info(f"Die Gruppe '{chat.title}' hat KEINE Themen aktiviert.")

    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Gruppeninformationen: {e}")

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

    logging.info("Abrufen der Gruppeninformationen beim Start...")
    # Abrufen der Gruppen-Infos beim Start
    await fetch_group_info(application)

    logging.info("Füge Nachrichten-Handler hinzu...")
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    logging.info("Starte den Bot...")
    await application.initialize()
    await application.start()
    logging.info("Bot läuft... Drücke STRG+C zum Beenden.")

    # Warten auf STRG+C
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende den Bot...")
    finally: