from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    topic_id = message.message_thread_id  # Die Themen-ID (falls vorhanden)
    user = message.from_user.username if message.from_user else "Unbekannt"
    text = message.text or ""  # Falls kein Text existiert, setzen wir ihn auf ""

    # Konsolenausgabe aller relevanten Informationen
    print(f"📩 Nachricht empfangen:")
    print(f"    Von: @{user}")
    print(f"    Chat-ID: {chat_id}")
    print(f"    Thema-ID: {topic_id}")
    print(f"    Nachricht: {text}")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Nachrichten-Handler hinzufügen
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot wird gestartet und wartet auf Nachrichten...")
    application.run_polling()

if __name__ == "__main__":
    main()