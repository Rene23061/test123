from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7773343880:AAEA6DSuxsymdll5A7lcWMSERsmjbNSh9eI"

# --- Befehl: /id (Zeigt die Gruppen-ID an) ---
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton("📋 In Zwischenablage kopieren", callback_data=f"copy_{chat_id}")],
        [InlineKeyboardButton("❌ Schließen", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"📌 **Gruppen-ID:** `{chat_id}`", parse_mode="Markdown", reply_markup=reply_markup)

# --- Callback-Funktion für Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("copy_"):
        chat_id = query.data.split("_")[1]
        await query.answer(f"Gruppen-ID {chat_id} kopiert! ✅", show_alert=True)

    elif query.data == "close":
        await query.message.delete()

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehl für Gruppen-ID
    application.add_handler(CommandHandler("id", get_group_id))

    # Callback für die Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 ID-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()