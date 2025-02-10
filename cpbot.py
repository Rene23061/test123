import logging
import asyncio
from telegram import Chat, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("telegram").setLevel(logging.DEBUG)

logging.info("Bot wird gestartet...")

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Gruppeninformationen auslesen ---
async def fetch_group_info(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Lese Gruppen- und Themeninformationen aus...")

    # Liste aller bekannten Chats (bei größeren Anwendungen könnte man das erweitern)
    async for chat_id in context.application.bot.get_updates(offset=None):
        if chat_id.message:
            chat: Chat = chat_id.message.chat

            if chat.type in ["group", "supergroup"]:
                logging.info(f"Erfolgreich verbunden mit der Gruppe: {chat.title} (ID: {chat.id})")

                # Prüfen, ob die Gruppe Themen hat (verfügbar ab Supergruppen)
                if chat.is_forum:
                    logging.info(f"Die Gruppe '{chat.title}' hat Themen aktiviert.")

                    # Liste aller Themen ausgeben (falls unterstützt)
                    topics = await context.application.bot.get_forum_topic_list(chat_id=chat.id)
                    for topic in topics:
                        logging.info(f"Gefundenes Thema: {topic.name} (Thema-ID: {topic.id})")
                else:
                    logging.info(f"Die Gruppe '{chat.title}' hat KEINE Themen aktiviert.")
            else:
                logging.info(f"Verbunden mit einem nicht unterstützten Chat-Typ: {chat.type}")

# --- Nachricht behandeln ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    username = update.message.from_user.username if update.message.from_user else "Unbekannt"
    chat_id = update.message.chat_id

    logging.info(f"Nachricht empfangen von @{username} in Chat {chat_id}: {message}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    logging.info("Initialisiere die Anwendung...")
    application = Application.builder().token(TOKEN).build()

    logging.info("Prüfe Gruppeninformationen...")
    # Prüfe Gruppen- und Themeninformationen beim Start
    application.job_queue.run_once(fetch_group_info, 0)

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
        await application.stop()
        await application.shutdown()
        logging.info("Bot wurde erfolgreich beendet.")

if __name__ == '__main__':
    asyncio.run(main())