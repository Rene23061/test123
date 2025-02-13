from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# Dein Bot-Token
BOT_TOKEN = "7720861006:AAGbTV0_haSgPhtNsv2unqy6ZiyI7A_BrBU"

def delete_system_messages(update: Update, context: CallbackContext):
    """Löscht Systemnachrichten wie Beitritt, Austritt oder angepinnte Nachrichten."""
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member or update.message.pinned_message:
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            print("✅ Systemnachricht gelöscht")

def main():
    """Startet den Telegram-Bot"""
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Überwacht Systemnachrichten und löscht sie
    dp.add_handler(MessageHandler(Filters.status_update, delete_system_messages))

    print("🚀 Bot läuft und löscht neue Systemnachrichten...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
