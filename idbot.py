import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    print("✅ Datenbank erfolgreich initialisiert.")
    return conn, cursor

# --- Befehl: /listids (Zeigt alle erlaubten Gruppen-IDs an) ---
async def list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT chat_id FROM allowed_groups")
    ids = cursor.fetchall()

    if ids:
        response = "📋 **Erlaubte Gruppen-IDs:**\n" + "\n".join(f"- `{id[0]}`" for id in ids)
    else:
        response = "❌ Es sind derzeit keine Gruppen-IDs gespeichert."

    await update.message.reply_text(response, parse_mode="Markdown")

# --- Befehl: /addid <ID> (Fügt eine neue Gruppen-ID hinzu) ---
async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib eine gültige Gruppen-ID an. Beispiel: /addid -4794368721")
        return

    chat_id = context.args[0].strip()

    try:
        cursor.execute("INSERT INTO allowed_groups (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Die Gruppen-ID `{chat_id}` wurde erfolgreich hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Diese Gruppen-ID ist bereits gespeichert.")

# --- Befehl: /delid <ID> (Löscht eine Gruppen-ID) ---
async def delete_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib eine gültige Gruppen-ID an. Beispiel: /delid -4794368721")
        return

    chat_id = context.args[0].strip()

    cursor.execute("DELETE FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Die Gruppen-ID `{chat_id}` wurde erfolgreich gelöscht.")
    else:
        await update.message.reply_text(f"⚠️ Die Gruppen-ID `{chat_id}` wurde nicht gefunden.")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle hinzufügen
    application.add_handler(CommandHandler("listids", list_ids))
    application.add_handler(CommandHandler("addid", add_id))
    application.add_handler(CommandHandler("delid", delete_id))

    print("🤖 ID-Bot wird gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()
