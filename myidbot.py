from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7773343880:AAEA6DSuxsymdll5A7lcWMSERsmjbNSh9eI"

# --- Prüfen, ob der Nutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int):
    try:
        chat_member = await update.effective_chat.get_member(user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# --- Befehl: /id (Nur für Admins/Gruppeninhaber) ---
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.effective_user.id

    # Prüfen, ob der Nutzer Admin ist
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ Nur Admins oder der Gruppeninhaber können diesen Befehl nutzen.")
        return

    keyboard = [[InlineKeyboardButton("❌ Schließen", callback_data="close")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"📌 **Gruppen-ID:** `{chat_id}`", parse_mode="Markdown", reply_markup=reply_markup)

# --- Callback-Funktion für den „Schließen“-Button ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "close":
        await query.message.delete()

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehl für Gruppen-ID (nur für Admins/Gruppeninhaber)
    application.add_handler(CommandHandler("id", get_group_id))

    # Callback für den „Schließen“-Button
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 ID-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()