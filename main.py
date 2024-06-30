#### File `main.py`

```python
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import sqlite3
import random
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')

# Configura il logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Collegamento al database SQLite
conn = sqlite3.connect('bot.db')
c = conn.cursor()

# Creazione delle tabelle nel database
def create_tables():
    with conn:
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, invites INTEGER DEFAULT 0, reflink TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ref_links (link TEXT PRIMARY KEY, user_id INTEGER)''')

create_tables()

# Funzione per inizializzare il bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Benvenuto nel bot!')

# Funzione per gestire l'entrata di un nuovo utente nel gruppo free
def welcome_new_user(update: Update, context: CallbackContext) -> None:
    new_members = update.message.new_chat_members
    for member in new_members:
        if member.id != context.bot.id:
            captcha = generate_captcha()
            context.user_data['captcha'] = captcha
            update.message.reply_text(f'Benvenuto {member.first_name}! Per favore, risolvi questo captcha: {captcha}')

def generate_captcha():
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    return f'{num1} + {num2}'

def verify_captcha(update: Update, context: CallbackContext) -> None:
    user_response = update.message.text
    captcha = context.user_data.get('captcha')
    if captcha:
        num1, num2 = map(int, captcha.split(' + '))
        if user_response == str(num1 + num2):
            update.message.reply_text('Captcha corretto! Invita 3 persone al gruppo free per accedere al gruppo VIP.')
            generate_ref_link(update, context)
        else:
            update.message.reply_text('Captcha errato. Riprova: ' + captcha)

def generate_ref_link(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    reflink = f'https://t.me/+naRTJEejM79iMTE0?start={user_id}'
    with conn:
        c.execute('INSERT OR IGNORE INTO users (user_id, reflink) VALUES (?, ?)', (user_id, reflink))
        c.execute('INSERT OR IGNORE INTO ref_links (link, user_id) VALUES (?, ?)', (reflink, user_id))
    update.message.reply_text(f'Ecco il tuo link di invito: {reflink}')

# Funzione per controllare il numero di inviti
def check_invites(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    with conn:
        c.execute('SELECT invites FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result:
            invites = result[0]
            update.message.reply_text(f'Hai invitato {invites} persone. Te ne mancano {3 - invites} per accedere al gruppo VIP.')

# Funzione per monitorare gli inviti
def track_invites(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    with conn:
        c.execute('SELECT invites FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0] >= 3:
            query.answer('Hai già accesso al gruppo VIP!')
        else:
            query.answer('Non hai ancora raggiunto il numero di inviti richiesto.')

def main() -> None:
    updater = Updater(TELEGRAM_API_KEY)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome_new_user))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, verify_captcha))
    dispatcher.add_handler(CommandHandler("ref", check_invites))
    dispatcher.add_handler(CallbackQueryHandler(track_invites))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
