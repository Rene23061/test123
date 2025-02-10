import sqlite3
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import re
import logging
import asyncio

# --- Logging konfigurieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
    return result is not None

# --- Überprüfung der Telegram-Nachrichten ---
async def check_telegram_links(update, context):
    message = update.message.text
    links = re.findall(r"(https?:\/\/)?t\.me\/[a-zA-Z0-9_-]+", message)

    for link in links:
        if not is_whitelisted(link):
            await update.message.delete()
            await update.message.reply_text(
                f"Dieser Link ist nicht erlaubt: {link}\nBitte kontaktiere einen Admin zur Freigabe."
            )
            return

# --- Befehl /link zum Hinzufügen eines Links zur Whitelist ---
async def add_link(update, context):
    if len(context.args) != 1:
        await update.message.reply_text("Bitte benutze: /link <URL>")
        return

    link = context.args[0].strip()
    if re.match(r"(https?:\/\/)?t\.me\/[a-zA-Z0-9_-]+", link):
        if add_to_whitelist(link):
            await update.message.reply_text(f"Link erfolgreich freigegeben: {link}")
        else:
            await update.message.reply_text("Der Link wurde bereits freigegeben.")
    else:
        await update.message.reply_text("Ungültiger Telegram-Link. Nur t.me-Links sind erlaubt.")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    application = Application.builder().token(TOKEN).build()

    # Handler hinzufügen
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_telegram_links))
    application.add_handler(CommandHandler("link", add_link))

    # Bot starten
    await application.initialize()
    await application.start()
    logging.info("Bot läuft... Drücke STRG+C zum Beenden.")

    # Warten, bis STRG+C gedrückt wird
    try:
        await asyncio.Future()  # Unendliches Warten (ersetzt problematische Warteschleifen)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende den Bot...")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())