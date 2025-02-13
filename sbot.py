import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Dein Bot-Token
BOT_TOKEN = "7720861006:AAGbTV0_haSgPhtNsv2unqy6ZiyI7A_BrBU"

async def delete_system_messages(update: Update, context: CallbackContext):
    """Löscht Systemnachrichten wie Beitritt, Austritt oder angepinnte Nachrichten."""
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member or update.message.pinned_message:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            print("✅ Systemnachricht gelöscht")

async def main():
    """Startet den Telegram-Bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Überwacht Systemnachrichten und löscht sie
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_system_messages))

    print("🚀 Bot läuft und löscht neue Systemnachrichten...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())