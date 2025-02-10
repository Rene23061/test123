import logging
import asyncio
from telegram.ext import Application

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logging.info("Bot wird gestartet...")

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Gruppeninformationen abrufen ---
async def fetch_group_and_topics(application):
    try:
        # Hole die letzten Updates, um die Gruppen-ID dynamisch zu finden
        updates = await application.bot.get_updates()

        # Suche nach der ersten relevanten Gruppen-Nachricht
        for update in updates:
            if update.message and (update.message.chat.type == "group" or update.message.chat.type == "supergroup"):
                chat = update.message.chat

                logging.info(f"Erfolgreich verbunden mit der Gruppe: {chat.title} (ID: {chat.id})")

                # Prüfe, ob die Gruppe Themen (Foren) unterstützt
                if chat.is_forum:
                    logging.info(f"Die Gruppe '{chat.title}' hat Themen aktiviert.")
                    topics = await application.bot.get_forum_topic_list(chat.id)
                    
                    for topic in topics:
                        logging.info(f"Gefundenes Thema: {topic.name} (Thema-ID: {topic.id})")
                else:
                    logging.info(f"Die Gruppe '{chat.title}' hat KEINE Themen aktiviert.")
                
                return  # Sobald eine Gruppe gefunden ist, beenden wir die Suche

        logging.info("Keine Gruppen mit relevanten Nachrichten gefunden.")
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Gruppeninformationen: {e}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    logging.info("Initialisiere die Anwendung...")
    application = Application.builder().token(TOKEN).build()

    logging.info("Hole Gruppen- und Themeninformationen...")
    await fetch_group_and_topics(application)

    logging.info("Bot wurde erfolgreich gestartet. Keine weiteren Aktionen konfiguriert.")
    await application.initialize()
    await application.start()

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