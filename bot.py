import re
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackContext, filters

TOKEN = "7622465777:AAFmKGf99ARh22mmw4Ex2jAdU2MBCZIs7VY"

# Themen mit Regeln (message_thread_id)
THEMEN_REGELN = {
    "lesen_nur": [1049, 2, 3, 913, 914],      # Nur Lesen erlaubt (löscht alle Nachrichten von Nicht-Admins)
    "medien_only": [912],    # Nur Bilder/Videos erlaubt
    "links_erlaubt": [911],  # Alle Links werden gelöscht, außer erlaubte
}

# Liste mit erlaubten Links
ERLAUBTE_LINKS = [
    "https://t.me/+oADbpc7pjyY2NDcy",
    "https://t.me/+5LKWu1RZHrU5ZGUy",
    "https://t.me/+qgzN9e4x42k1NzQy",
    "https://t.me/+uj_H5Ikzfzg4OTVi",
    "https://t.me/+2N4rEE4TiVQ0M2Qy",
    "https://t.me/+vjLkkXIk7qZlNDdi",
    "https://t.me/ZoeysAOGBStuttgart",
    "https://t.me/ZoeysAOGBFFM",
    "https://t.me/+RrE9ihQCowcxM2Ni",
    "https://t.me/+J5BC_ulfaNgzNmMy",
    "https://t.me/+zR0wr1A4BnZhMzFi",
    "https://t.me/+tjOhC2Zw9EFmOGIy"
]

# Regulärer Ausdruck zur Erkennung von URLs
URL_PATTERN = re.compile(
    r'((http|https):\/\/)?'  # optionales Protokoll
    r'(www\.)?'              # optionales 'www.'
    r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.'  # Domainname
    r'[a-zA-Z0-9()]{1,6}\b'  # Top-Level-Domain
    r'([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'  # Pfad
)

# Nachrichtenkontrolle
async def kontrolliere_nachricht(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    text = message.text or ""  # Falls kein Text existiert, setzen wir ihn auf einen leeren String
    topic_id = message.message_thread_id  # Die echte Themen-ID holen

    print(f"Nachricht erhalten: {text}")
    print(f"message_thread_id (Thema): {topic_id}")

    chat_member = await context.bot.get_chat_member(chat_id, user.id)
    is_admin = chat_member.status in ["administrator", "creator"]
    print(f"Benutzer ist Admin: {is_admin}")

    # Standard-Kategorie
    erkannte_kategorie = "alles_erlaubt (Hauptchat oder nicht spezifiziert)"

    # ❌ Thema: "lesen_nur" → Alle Nachrichten löschen, außer von Admins
    if topic_id in THEMEN_REGELN["lesen_nur"]:
        erkannte_kategorie = "lesen_nur (Nur Lesen erlaubt)"
        if not is_admin:
            print("❌ Nachricht wird gelöscht (Nur Lesen erlaubt)")
            await context.bot.delete_message(chat_id, message.message_id)

    # ❌ Thema: "medien_only" → Nur Bilder/Videos erlaubt, reine Texte/Links werden gelöscht
    elif topic_id in THEMEN_REGELN["medien_only"]:
        erkannte_kategorie = "medien_only (Nur Medien erlaubt)"

        # Prüfen, ob es sich um eine reine Textnachricht oder einen Link handelt
        ist_reiner_text = bool(text and not message.photo and not message.video)
        enthaelt_link = bool(URL_PATTERN.search(text)) and not any(link in text for link in ERLAUBTE_LINKS)

        if ist_reiner_text or enthaelt_link:
            print("❌ Nachricht wird gelöscht (Nur Medien + Beschreibung erlaubt)")
            await context.bot.delete_message(chat_id, message.message_id)

    # ❌ Thema: "links_erlaubt" → Alle Links werden gelöscht, außer den erlaubten
    elif topic_id in THEMEN_REGELN["links_erlaubt"]:
        erkannte_kategorie = "links_erlaubt (Alle Links werden gelöscht)"

        # Verbesserte Linkprüfung: Nur den exakten Link oder Varianten davon akzeptieren
        gefundene_links = [match.group(0) for match in URL_PATTERN.finditer(text)]

        # Prüfen, ob einer der gefundenen Links nicht erlaubt ist
        enthaelt_verbotene_links = any(
            not any(re.fullmatch(re.escape(erlaubter_link) + r'[\S]*', gefundener_link) for erlaubter_link in ERLAUBTE_LINKS)
            for gefundener_link in gefundene_links
        )

        if enthaelt_verbotene_links:
            print(f"❌ Verbotener Link gefunden und gelöscht: {text}")
            await context.bot.delete_message(chat_id, message.message_id)
            # Nachricht an den Benutzer senden, warum sie gelöscht wurde
            await context.bot.send_message(
                chat_id,
                "❌ Dein Link wurde gelöscht, da das Posten von unbekannten Links in diesem Thema nicht gestattet ist. Bitte kontaktiere einen Administrator, um zu prüfen, ob der Link freigegeben werden kann.",
                message_thread_id=topic_id  # Die aktuelle Themen-ID verwenden
            )

    print(f"✅ Kategorie erkannt: {erkannte_kategorie}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))
    print("Bot startet...")
    application.run_polling()

if __name__ == "__main__":
    main()