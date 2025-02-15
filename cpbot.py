import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Setze den Test-Token ein
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# Whitelist für erlaubte Links
whitelist = {}

# Logger einrichten
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

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

    if query.data == "add_link":
        await query.message.edit_text("Sende mir bitte den Link, den du zur Whitelist hinzufügen möchtest.")

        # Warte auf die nächste Nachricht mit einem Link
        context.user_data["awaiting_link"] = True

    elif query.data == "show_links":
        if not whitelist:
            await query.message.edit_text("❌ Die Whitelist ist leer.")
        else:
            links = "\n".join(whitelist.keys())
            keyboard = [[InlineKeyboardButton("❌ Link löschen", callback_data=f"delete_{link}")] for link in whitelist.keys()]
            keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(f"✅ Whitelist:\n{links}", reply_markup=reply_markup)

    elif query.data.startswith("delete_"):
        link_to_delete = query.data.replace("delete_", "")
        if link_to_delete in whitelist:
            del whitelist[link_to_delete]
            await query.message.edit_text(f"✅ Der Link wurde entfernt: {link_to_delete}")
        else:
            await query.message.edit_text("❌ Link nicht gefunden.")

    elif query.data == "close_menu":
        await query.message.delete()

# Nachricht prüfen und ggf. löschen
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.entities:
        for entity in message.entities:
            if entity.type == "url":
                link = message.text[entity.offset: entity.offset + entity.length]
                if link not in whitelist:
                    await message.delete()
                    await message.reply_text(f"⚠️ Dieser Link ist nicht erlaubt und wurde entfernt: {link}")
                    return

# Funktion zum Link-Speichern
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_link" in context.user_data and context.user_data["awaiting_link"]:
        link = update.message.text
        whitelist[link] = True
        context.user_data["awaiting_link"] = False
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")

# Hauptfunktion zum Starten des Bots
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), check_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    application.run_polling()

if __name__ == "__main__":
    main()