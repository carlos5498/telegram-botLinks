import os
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")
try:
    MY_ID = int(os.getenv("MY_ID", "0"))
except:
    MY_ID = 0

PASSWORD_CORRECTA = "Carlos13mar"

config = {
    "welcome_msg": "¡Bienvenido {MENTION}!",
    "autorizados": {MY_ID} if MY_ID != 0 else set(),
    "last_msg_ids": {} 
}

# --- SERVIDOR WEB (Obligatorio para Render) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Active")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# --- LÓGICA DE BIENVENIDA (Sin necesidad de ser Admin) ---
async def check_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo se activa cuando Telegram detecta que alguien se unió
    if update.message.new_chat_members:
        chat_id = update.effective_chat.id
        
        # 1. Intentar borrar el mensaje anterior del BOT en ese grupo
        if chat_id in config["last_msg_ids"]:
            try:
                await context.bot.delete_message(chat_id, config["last_msg_ids"][chat_id])
            except Exception:
                # Si ya fue borrado manualmente o expiró, lo ignoramos
                pass 

        # 2. Saludar a los nuevos (pueden ser varios si entran de golpe)
        for user in update.message.new_chat_members:
            mention = user.mention_html()
            text = config["welcome_msg"].replace("{MENTION}", mention)
            
            try:
                sent_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML"
                )
                # 3. Guardar el ID para borrarlo cuando entre el siguiente
                config["last_msg_ids"][chat_id] = sent_msg.message_id
            except Exception as e:
                logging.error(f"Error al enviar mensaje: {e}")

# --- PANEL DE ADMINISTRACIÓN ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.chat.type == "private":
        if user_id not in config["autorizados"]:
            await update.message.reply_text("❌ Sin acceso. Envía la contraseña.")
            return
        
        btn = [[InlineKeyboardButton("Configurar Mensaje 📝", callback_data="set_msg")]]
        await update.message.reply_text(
            f"Configuración actual:\n`{config['welcome_msg']}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btn)
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Activar admin con contraseña
    if text == PASSWORD_CORRECTA:
        config["autorizados"].add(user_id)
        await update.message.reply_text("✅ Ahora eres administrador. Usa /start para configurar.")
        return

    # Guardar nuevo mensaje personalizable
    if user_id in config["autorizados"] and context.user_data.get("state") == "waiting_msg":
        config["welcome_msg"] = text
        context.user_data["state"] = None
        await update.message.reply_text("✅ Mensaje guardado correctamente.")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "set_msg":
        context.user_data["state"] = "waiting_msg"
        await query.edit_message_text("Envíame el nuevo mensaje. Recuerda incluir `{MENTION}`.")

# --- INICIO DEL BOT ---
def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    # Filtro para detectar actualizaciones de estado (como nuevos miembros)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_new_members))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    app.run_polling()

if __name__ == '__main__':
    main()
