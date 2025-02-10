import sqlite3
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import re
import logging
import asyncio

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Auf DEBUG gesetzt, damit alle Details angezeigt werden
)
logging.info("Bot wird gestartet...")

# --- Initialisiere die Datenbank ---
def init_db():
    conn = sqlite3.connect('whitelist.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS whitelist (link TEXT PRIMARY KEY)')
    conn.commit()
    logging.info("Datenbank erfolgreich initialisiert.")
    return conn, cursor

conn, cursor = init_db()

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Hinzufügen eines Links zur Whitelist ---
def add_to_whitelist(link):
    try:
        cursor.execute('INSERT INTO whitelist (link) VALUES (?)', (link,))
        conn.commit()
        logging.info(f"Link zur Whitelist hinzugefügt: {link}")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Link existiert bereits in der Whitelist: {link}")
        return False

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(link):
    cursor.execute('SELECT link FROM whitelist WHERE link = ?', (link,))
    result = cursor.fetchone()
    if result:
        logging.debug(f"Link ist in der Whitelist: {link}")
    else:
        logging.debug(f"Link ist NICHT in der Whitelist: {link}")
    return result is not None

# --- Überprüfung der Telegram-Nachrichten ---
async def check_telegram_links(update, context):
    message = update.message.text
    username = update.message.from_user.username if update.message.from_user else "Unbekannt"
    chat_id = update.message.chat_id

    logging.info(f"Nachricht von @{username} in Chat {chat_id}: {message}")
    
    # Alle Telegram-Gruppen-Links filtern
    links = re.findall(r"(https?:\/\/)?t\.me\/[a-zA-Z0-9_-]+", message)

    if not links:
        logging.debug("Keine Telegram-Links in der Nachricht gefunden.")
        return

    for link in links:
        logging.info(f"Erkannter Link: {link}")
        if not is_whitelisted(link):
            logging.warning(f"Unerlaubter Link erkannt: {link}. Nachricht wird gelöscht.")
            await update.message.delete()
            await update.message.reply_text(
                f"Dieser Link ist nicht erlaubt: {link}\nBitte kontaktiere einen Admin zur Freigabe."
            )
            return
        else:
            logging.info(f"Erlaubter Link: {link}")

# --- Befehl /link zum Hinzufügen eines Links zur Whitelist ---
async def add_link(update, context):
    if len(context.args) != 1:
        await update.message.reply_text("Bitte benutze: /link <URL>")
        logging.warning(f"/link-Befehl ohne gültige Argumente empfangen.")
        return

    link = context.args[0].strip()
    if re.match(r"(https?:\/\/)?t\.me\/[a-zA-Z0-9_-]+", link):
        if add_to_whitelist(link):
            await update.message.reply_text(f"Link erfolgreich freigegeben: {link}")
            logging.info(f"Link erfolgreich zur Whitelist hinzugefügt: {link}")
        else:
            await update.message.reply_text("Der Link wurde bereits freigegeben.")
            logging.info(f"Link bereits in der Whitelist: {link}")
    else:
        await update.message.reply_text("Ungültiger Telegram-Link. Nur t.me-Links sind erlaubt.")
        logging.warning(f"Ungültiger Link wurde gesendet: {link}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    application = Application.builder().token(TOKEN).build()

    # Handler hinzufügen
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_telegram_links))
    application.add_handler(CommandHandler("link", add_link))

    # Bot starten
    await application.initialize()
    await application.start()
    logging.info("Bot läuft... Drücke STRG+C zum Beenden.")

    # Warten, bis STRG+C gedrückt wird
    try:
        await asyncio.Future()  # Unendliches Warten
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende den Bot...")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())