import sqlite3
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import re
import logging
import asyncio

# --- Logging konfigurieren ---
logging.basicConfig(
    filename="bot_debug.log",
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
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
        logging.info(f"Link ist in der Whitelist: {link}")
    else:
        logging.info(f"Link ist NICHT in der Whitelist: {link}")
    return result is not None

# --- Überprüfung der Nachrichten in der Gruppe ---
async def check_telegram_links(update, context):
    message = update.message.text
    username = update.message.from_user.username
    chat_id = update.message.chat_id

    logging.info(f"Prüfe Nachricht von @{username} in Chat {chat_id}: {message}")
    links = re.findall(r"(https?:\/\/)?t\.me\/\S+", message)

    for link in links:
        if not is_whitelisted(link):
            logging.warning(f"Unerlaubter Link erkannt und gelöscht: {link}")
            await update.message.delete()
            await update.message.reply_text(
                f"Dieser Link ist nicht erlaubt: {link}\nBitte kontaktiere einen Admin zur Freigabe."
            )
            return

# --- Befehl /link zum Hinzufügen von Links zur Whitelist ---
async def add_link(update, context):
    username = update.message.from_user.username
    logging.info(f"/link-Befehl empfangen von @{username}")

    if len(context.args) != 1:
        await update.message.reply_text("Bitte benutze: /link <URL>")
        logging.warning(f"Falsche Eingabe von @{username}: /link-Befehl ohne gültige URL")
        return

    link = context.args[0].strip()
    if re.match(r"(https?:\/\/)?t\.me\/\S+", link):
        if add_to_whitelist(link):
            await update.message.reply_text(f"Link erfolgreich freigegeben: {link}")
        else:
            await update.message.reply_text("Der Link wurde bereits freigegeben.")
    else:
        await update.message.reply_text("Ungültiger Telegram-Link. Nur t.me-Links sind erlaubt.")
        logging.warning(f"Ungültiger Link von @{username}: {link}")

# --- Hauptfunktion zum Starten des Bots ---
async def main():
    logging.info("Bot wird initialisiert.")
    
    # Bot-Initialisierung
    application = Application.builder().token(TOKEN).build()

    # Handler für Gruppen-Nachrichten
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_telegram_links))

    # Handler für den Befehl /link
    application.add_handler(CommandHandler("link", add_link))

    # Ereignis, um den Bot bei KeyboardInterrupt zu stoppen
    stop_event = asyncio.Event()

    async def stop_bot(*args):
        logging.info("Empfange Stop-Signal, beende den Bot...")
        stop_event.set()

    # Registriere Signal-Handler
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(asyncio.CancelledError, lambda: asyncio.create_task(stop_bot()))

    # Bot starten und sauber beenden
    await application.initialize()
    try:
        await application.start()
        await application.updater.start_polling()
        logging.info("Bot läuft... Drücke STRG+C zum Beenden.")
        await stop_event.wait()  # Warten, bis das Stop-Signal empfangen wird
    except Exception as e:
        logging.error(f"Fehler während der Laufzeit: {e}")
    finally:
        logging.info("Beende den Bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot durch STRG+C beendet.")