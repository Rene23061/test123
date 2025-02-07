from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import calendar
from datetime import datetime, timedelta
import logging

# Logging einrichten
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Funktion zur Erstellung des Inline-Kalenders
def erstelle_inline_kalender() -> InlineKeyboardMarkup:
    today = datetime.today()
    jahr, monat = today.year, today.month
    heutiger_tag = today.day

    cal = calendar.monthcalendar(jahr, monat)
    tastatur = []

    # Zeilenweise die Tage als Buttons darstellen
    for woche in cal:
        reihe = []
        for tag in woche:
            if tag == 0 or tag < heutiger_tag:  # Leere Felder oder Tage vor heute ignorieren
                reihe.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                reihe.append(InlineKeyboardButton(str(tag), callback_data=f"tag_{tag}_{monat}_{jahr}"))
        tastatur.append(reihe)

    return InlineKeyboardMarkup(tastatur)

# Funktion zur Erstellung der Inline-Tastatur für Uhrzeiten
def erstelle_zeit_tastatur() -> InlineKeyboardMarkup:
    zeiten = [("10:00 - 12:00", "10_12"), ("12:00 - 14:00", "12_14"), ("14:00 - 16:00", "14_16"),
              ("16:00 - 18:00", "16_18"), ("18:00 - 20:00", "18_20"), ("20:00 - 22:00", "20_22")]

    # Jede Uhrzeit in einer eigenen Zeile
    tastatur = [[InlineKeyboardButton(text, callback_data=f"zeit_{data}")] for text, data in zeiten]
    return InlineKeyboardMarkup(tastatur)

# Funktion zum Anzeigen des Kalenders
async def zeige_kalender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Inline-Tastatur-Kalender erstellen
        tastatur = erstelle_inline_kalender()

        # Kalender als Nachricht senden
        await update.message.reply_text(
            "🔥 Hey du, hier kannst du dir deinen ganz persönlichen Wunschtermin sichern 😏💋\n\n"
            "Aber bedenke: Wenn dein Termin länger als 3 Tage in der Zukunft liegt, ist eine Anzahlung von 25% nötig. 💸 Warum? Weil leider viel zu oft Treffen kurzfristig abgesagt werden – und das raubt uns beiden nur den Spaß. Diese kleine Anzahlung zeigt, dass du es wirklich ernst meinst und bereit bist, dich voll auf dieses heiße Erlebnis einzulassen. Ohne die Anzahlung wird dein Termin nicht bestätigt. ❌\n\n"
            "Also, worauf wartest du noch? \n\n"
            "Wähle ein Datum aus: 📅",
            reply_markup=tastatur
        )
    except Exception as e:
        logger.error(f"Fehler beim Anzeigen des Kalenders: {e}")

# Funktion zur Verarbeitung der Auswahl eines Tages
async def tag_ausgewaehlt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    try:
        # Versuche die Abfrage zu beantworten
        await query.answer()
    except Exception as e:
        logger.warning(f"Warnung beim Beantworten der Callback-Abfrage: {e}")

    # Datum aus den Callback-Daten extrahieren
    _, tag, monat, jahr = query.data.split("_")
    context.user_data['ausgewaehltes_datum'] = f"{int(tag):02d}.{int(monat):02d}.{jahr}"

    # Nachricht aktualisieren und die Uhrzeitauswahl anzeigen
    await query.edit_message_text(
        f"Schon heiß auf unser Treffen? 🔥 Du hast den {context.user_data['ausgewaehltes_datum']} gewählt – eine perfekte Entscheidung. 😏💋\n\n"
        "Jetzt bleibt nur noch die Frage: Um wie viel Uhr möchtest du erscheinen, damit wir uns endlich näherkommen? ⏰🍓\n\n"
        "Wähle unten die passende Uhrzeit aus:",
        reply_markup=erstelle_zeit_tastatur()
    )

# Funktion zur Verarbeitung der Uhrzeitauswahl
async def zeit_ausgewaehlt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    try:
        # Versuche die Abfrage zu beantworten
        await query.answer()
    except Exception as e:
        logger.warning(f"Warnung beim Beantworten der Callback-Abfrage: {e}")

    # Uhrzeit aus den Callback-Daten extrahieren
    _, start, ende = query.data.split("_")
    ausgewaehlte_uhrzeit = f"{start}:00 - {ende}:00"

    # Ausgewähltes Datum aus dem Kontext holen
    ausgewaehltes_datum = context.user_data['ausgewaehltes_datum']

    # Benutzerinformationen abrufen
    benutzer_vorname = query.from_user.first_name
    benutzer_username = f"@{query.from_user.username}" if query.from_user.username else "(kein Benutzername)"

    # Bestätigungstext
    text = (
        f"Sehr schön 😏 Du hättest gern einen Termin am {ausgewaehltes_datum} von {ausgewaehlte_uhrzeit} Uhr. 🔥💋\n\n"
        "Ich werde mich schnellstmöglich bei dir melden, damit nichts mehr zwischen uns steht und wir uns ganz unseren Fantasien hingeben können. 😈🍓 Freu dich schon mal auf das, was kommt …"
    )

    # Datum in ein datetime-Objekt umwandeln
    termin_datum = datetime.strptime(ausgewaehltes_datum, "%d.%m.%Y")
    heute = datetime.today()

    # Wenn der Termin mehr als 3 Tage in der Zukunft liegt, zusätzliche Nachricht senden
    if (termin_datum - heute).days > 3:
        text += (
            f"\n\nDer von dir gewählte Termin am {ausgewaehltes_datum} von {ausgewaehlte_uhrzeit} Uhr liegt mehr als 3 Tage in der Zukunft. 😏💋\n\n"
            "Da es in der Vergangenheit leider öfter zu kurzfristigen Absagen gekommen ist, ist eine kleine Anzahlung von 25% nötig, um den Termin verbindlich zu machen. 💸🔥 "
            "Diese Anzahlung zeigt mir, dass du es wirklich ernst meinst und genauso heiß auf unser Treffen bist wie ich. \n\n"
            "Ich werde mich schnellstmöglich bei dir melden, damit wir alle Details klären und unser Verlangen bald zur Realität wird. 🍓😈 "
            "Sollten unvorhergesehene Umstände meinerseits das Treffen verhindern, bekommst du die Anzahlung selbstverständlich zurück. ✅"
        )

    # Nachricht aktualisieren
    await query.edit_message_text(text)

    # Private Nachricht an den Benutzer senden
    benutzer_id = query.from_user.id
    nachricht = f"""
📅 <b>Dein Terminwunsch</b>
Benutzer: {benutzer_vorname} ({benutzer_username})
Datum: {ausgewaehltes_datum}
Zeit: {ausgewaehlte_uhrzeit} Uhr
"""
    await context.bot.send_message(chat_id=benutzer_id, text=nachricht, parse_mode="HTML")

    # Nachricht an den Admin senden
    admin_id = 6093614638  # Deine Admin-Chat-ID
    admin_nachricht = f"""
🚨 <b>Neuer Termin angefragt!!</b>
Benutzer: {benutzer_vorname} ({benutzer_username})
Datum: {ausgewaehltes_datum}
Zeit: {ausgewaehlte_uhrzeit} Uhr
"""
    await context.bot.send_message(chat_id=admin_id, text=admin_nachricht, parse_mode="HTML")

# Funktion zum Abrufen der persönlichen Chat-ID
async def sende_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Deine persönliche Chat-ID ist: {chat_id}")

# Hauptfunktion zum Starten des Bots
def main():
    try:
        # Bot-Token einfügen
        application = Application.builder().token("7748690360:AAHJK1OWNfxN7JTsC6MVjQQwLKN0Yc5rn5A").build()

        # Befehle und Callback-Handler einrichten
        application.add_handler(CommandHandler("start", zeige_kalender))
        application.add_handler(CommandHandler("termine", zeige_kalender))
        application.add_handler(CommandHandler("meineid", sende_chat_id))  # Befehl zur Ausgabe der Chat-ID
        application.add_handler(CallbackQueryHandler(tag_ausgewaehlt, pattern="^tag_"))
        application.add_handler(CallbackQueryHandler(zeit_ausgewaehlt, pattern="^zeit_"))

        # Bot starten
        logger.info("Bot erfolgreich gestartet und läuft jetzt...")
        application.run_polling()
    except Exception as e:
        logger.error(f"Fehler beim Start des Bots: {e}")

if __name__ == "__main__":
    main()