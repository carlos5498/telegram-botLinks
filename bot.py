import telebot
from telebot import types
import threading
import time

API_TOKEN = 'TU_TOKEN_AQUI'
bot = telebot.TeleBot(API_TOKEN)

# Variables de control
PASSWORD = "Carlos13mar"
authorized_users = set()
target_link = "Esperando link..."
repeat_time = 600 # 10 min por defecto
pin_enabled = False
running_groups = {} # {group_id: threading.Event}

def auto_send_task(chat_id, stop_event):
    while not stop_event.is_set():
        msg = bot.send_message(chat_id, f"📢 Enlace oficial:\n{target_link}")
        if pin_enabled:
            try:
                bot.pin_chat_message(chat_id, msg.message_id)
            except:
                pass
        time.sleep(repeat_time)

@bot.message_handler(func=lambda message: message.chat.type == 'private')
def private_handler(message):
    # Validar contraseña
    if message.text == PASSWORD:
        authorized_users.add(message.from_user.id)
        bot.reply_to(message, "✅ Acceso concedido. Envíame el LINK que quieres promocionar.")
        return

    if message.from_user.id not in authorized_users:
        return # No responde nada si no hay contraseña

    # Si es usuario autorizado y manda un link
    if "http" in message.text:
        global target_link
        target_link = message.text
        bot.reply_to(message, f"🔗 Link actualizado a: {target_link}\nUsa /start para ver el menú de configuración.")
    
    elif message.text == "/start":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("10 min", callback_data="t_600")
        btn2 = types.InlineKeyboardButton("20 min", callback_data="t_1200")
        btn3 = types.InlineKeyboardButton("30 min", callback_data="t_1800")
        btn4 = types.InlineKeyboardButton("1h", callback_data="t_3600")
        btn5 = types.InlineKeyboardButton("Fijar: ON", callback_data="pin_on")
        btn6 = types.InlineKeyboardButton("Fijar: OFF", callback_data="pin_off")
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
        bot.send_message(message.chat.id, f"⚙️ Configuración actual:\nLink: {target_link}\nIntervalo: {repeat_time/60}min\nFijar: {pin_enabled}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global repeat_time, pin_enabled
    if call.data.startswith("t_"):
        repeat_time = int(call.data.split("_")[1])
        bot.answer_callback_query(call.id, f"Tiempo cambiado a {repeat_time/60} min")
    elif call.data == "pin_on":
        pin_enabled = True
        bot.answer_callback_query(call.id, "Fijado activado")
    elif call.data == "pin_off":
        pin_enabled = False
        bot.answer_callback_query(call.id, "Fijado desactivado")

@bot.message_handler(commands=['start'])
def group_start(message):
    if message.chat.type in ['group', 'supergroup']:
        if message.from_user.id not in authorized_users:
            return
        
        chat_id = message.chat.id
        if chat_id in running_groups:
            bot.send_message(chat_id, "⚠️ El bot ya está corriendo en este grupo.")
            return

        stop_event = threading.Event()
        running_groups[chat_id] = stop_event
        thread = threading.Thread(target=auto_send_task, args=(chat_id, stop_event))
        thread.start()
        bot.send_message(chat_id, f"🚀 Promoción iniciada cada {repeat_time/60} min.")

bot.infinity_polling()
