import re
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Befehl: /link (Link zur Whitelist hinzufügen) ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib einen gültigen Link an. Beispiel: /link https://t.me/gruppe")
        return

    link = context.args[0].strip()

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Ungültiger Link! Beispiel: /link https://t.me/gruppe")
        return

    if is_whitelisted(chat_id, link):
        await update.message.reply_text("⚠️ Link ist bereits in der Whitelist.")
        return

    cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()
    await update.message.reply_text(f"✅ Link erfolgreich hinzugefügt: {link}")

# --- Befehl: /list (Whitelist anzeigen) ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Keine Links gespeichert."
    await update.message.reply_text(response, parse_mode="Markdown")

# --- Befehl: /del (Link löschen) ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib den Link an, den du löschen möchtest.")
        return

    link = context.args[0].strip()
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Link gelöscht: {link}")
    else:
        await update.message.reply_text("⚠️ Link nicht in der Whitelist.")

# --- Nachrichtenprüfung: Löscht unerlaubte Links ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        if not is_whitelisted(chat_id, link):
            await context.bot.delete_message(chat_id, message.message_id)
            await update.message.reply_text(
                f"🚫 {user.first_name}, dein Link wurde gelöscht. Nicht erlaubt!"
            )

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("link", add_link))
    application.add_handler(CommandHandler("list", list_links))
    application.add_handler(CommandHandler("del", delete_link))

    # Nachrichten filtern
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()