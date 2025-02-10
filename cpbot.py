import sqlite3
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import re

# --- Initialisiere die Datenbank ---
def init_db():
    conn = sqlite3.connect('whitelist.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS whitelist (link TEXT PRIMARY KEY)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Hinzufügen eines Links zur Whitelist ---
def add_to_whitelist(link):
    try:
        cursor.execute('INSERT INTO whitelist (link) VALUES (?)', (link,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Link existiert bereits

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(link):
    cursor.execute('SELECT link FROM whitelist WHERE link = ?', (link,))
    return cursor.fetchone() is not None

# --- Überprüfung der Nachrichten in der Gruppe ---
def check_telegram_links(update, context):
    message = update.message.text
    links = re.findall(r"(https?:\/\/)?t\.me\/\S+", message)

    for link in links:
        if not is_whitelisted(link):
            update.message.delete()
            update.message.reply_text(f"Dieser Link ist nicht erlaubt: {link}\nBitte kontaktiere einen Admin zur Freigabe.")
            return

# --- Befehl /link zum Hinzufügen von Links zur Whitelist ---
def add_link(update, context):
    if len(context.args) != 1:
        update.message.reply_text("Bitte benutze: /link <URL>")
        return

    link = context.args[0].strip()
    if re.match(r"(https?:\/\/)?t\.me\/\S+", link):
        if add_to_whitelist(link):
            update.message.reply_text(f"Link erfolgreich freigegeben: {link}")
        else:
            update.message.reply_text("Der Link wurde bereits freigegeben.")
    else:
        update.message.reply_text("Ungültiger Telegram-Link. Nur t.me-Links sind erlaubt.")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    # Bot-Initialisierung
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handler für Gruppen-Nachrichten
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_telegram_links))

    # Handler für den Befehl /link
    dp.add_handler(CommandHandler("link", add_link))

    # Bot starten
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()