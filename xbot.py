import sqlite3
from telegram.ext import Application

# ✅ Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# ✅ Verbindung zur Datenbank herstellen
def connect_db():
    try:
        conn = sqlite3.connect('shop_database.db')  # Falls die DB nicht existiert, wird sie erstellt
        cursor = conn.cursor()
        
        # Teste die Verbindung mit einer einfachen Abfrage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📡 Datenbank erfolgreich verbunden! Tabellen gefunden

Verstanden! Es scheint, dass es immer noch Probleme mit der Event-Loop-Verwaltung gibt. Da du die neuesten Bibliotheken verwendest und eine saubere Verbindung herstellen möchtest, gehen wir **schrittweise** vor, um nur die Datenbankverbindung zu testen und den Bot zu starten, ohne dass er direkt auf Fehler stößt.

---

## **Ziel:**
- Eine **saubere Verbindung zur Datenbank herstellen**.
- Den Bot **einfach starten**, ohne die Event-Loop-Probleme oder unnötige Komplexität.
- **Schritt für Schritt** die Funktionalität hinzufügen.

---

### **1️⃣ Minimaler Code für die Datenbankverbindung und den Bot-Start**

1. **Datenbank-Verbindung** herstellen, ohne den Bot sofort zu starten.  
2. **Bot starten**, aber ohne die `asyncio.run()`-Funktion zu verwenden, die die Event-Loop-Probleme verursacht.

Hier ist ein **sehr einfacher Code**:

### **Code in `xbot.py`**

```python
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank herstellen
def connect_db():
    try:
        conn = sqlite3.connect('shop_database.db')  # Falls die DB nicht existiert, wird sie erstellt
        cursor = conn.cursor()

        # Teste die Verbindung mit einer einfachen Abfrage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"📡 Datenbank erfolgreich verbunden! Tabellen gefunden: {tables}")
        conn.close()
    except Exception as e:
        print(f"⚠ Fehler bei der Datenbankverbindung: {e}")

# Start-Befehl für den Bot
def start(update: Update, context):
    update.message.reply_text("Bot ist erfolgreich gestartet und die Datenbank ist verbunden!")
    
# Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    app = Application.builder().token(TOKEN).build()

    # Datenbankverbindung testen
    connect_db()

    # Start-Befehl registrieren
    app.add_handler(CommandHandler("start", start))

    # Bot starten
    app.run_polling()

if __name__ == '__main__':
    main()