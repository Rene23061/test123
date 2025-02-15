import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Setze den Test-Token ein
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# Logger einrichten
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect("whitelist.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            link TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()

# Link in die Whitelist-Datenbank eintragen
def add_link_to_db(chat_id, link):
    conn = sqlite3.connect("whitelist.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO links (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Link existiert bereits
    finally:
        conn.close()

# Link aus der Datenbank löschen
def remove_link_from_db(chat_id, link):
    conn = sqlite3.connect("whitelist.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM links WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()
    conn.close()

# Alle Links einer Gruppe abrufen
def get_links_from_db(chat_id):
    conn = sqlite3.connect("whitelist.db")
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM links WHERE chat_id = ?", (chat_id,))
    links = [row[0] for row in cursor.fetchall()]
    conn.close()
    return links

# Funktion zum Starten des Bots
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Willkommen! Nutze /link, um das Menü zu öffnen.")

# Funktion zum Anzeigen des Menüs
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data="show_links")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Wähle eine Option:", reply_markup=reply_markup)

# Callback-Funktion für Inline-Buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "add_link":
        await query.message.edit_text("Sende mir bitte den Link, den du zur Whitelist hinzufügen möchtest.")
        context.user_data["awaiting_link"] = chat_id  # Warte auf Link von diesem Chat

    elif query.data == "show_links":
        links = get_links_from_db(chat_id)
        if not links:
            await query.message.edit_text("❌ Die Whitelist ist leer.")
        else:
            keyboard = [[InlineKeyboardButton(f"❌ {link}", callback_data=f"delete_{link}")] for link in links]
            keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(f"✅ Whitelist:\n" + "\n".join(links), reply_markup=reply_markup)

    elif query.data.startswith("delete_"):
        link_to_delete = query.data.replace("delete_", "")
        remove_link_from_db(chat_id, link_to_delete)
        await query.message.edit_text(f"✅ Der Link wurde entfernt: {link_to_delete}")

    elif query.data == "close_menu":
        await query.message.delete()

# Nachricht prüfen und ggf. löschen
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if message.entities:
        for entity in message.entities:
            if entity.type == "url":
                link = message.text[entity.offset: entity.offset + entity.length]
                if link not in get_links_from_db(chat_id):
                    await message.delete()
                    await message.reply_text(f"⚠️ Dieser Link ist nicht erlaubt und wurde entfernt: {link}")

# Funktion zum Speichern eines Links
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_link" in context.user_data:
        chat_id = context.user_data["awaiting_link"]
        link = update.message.text

        if add_link_to_db(chat_id, link):
            await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
        else:
            await update.message.reply_text(f"⚠️ **{link}** ist bereits in der Whitelist.")

        del context.user_data["awaiting_link"]

# Hauptfunktion zum Starten des Bots
def main():
    init_db()  # Datenbank initialisieren
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), check_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    application.run_polling()

if __name__ == "__main__":
    main()