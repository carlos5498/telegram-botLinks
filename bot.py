import os
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")
try:
    MY_ID = int(os.getenv("MY_ID", "0"))
except:
    MY_ID = 0

PASSWORD_CORRECTA = "Carlos13mar"

# Estructura de datos
config = {
    "welcome_msg": "¡Bienvenido {MENTION} al grupo!",
    "autorizados": {MY_ID} if MY_ID != 0 else set(),
    "last_msg_ids": {} # {chat_id: message_id} para borrar el anterior
}

# --- SERVIDOR WEB (Para Render) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot de Bienvenida Operativo")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# --- LÓGICA DE BIENVENIDA ---
async def on_user_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    # Solo actuar si el estado cambia a 'member' (alguien se une)
    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status == "member":
        chat_id = update.effective_chat.id
        user = result.new_chat_member.user
        mention = user.mention_html()
        
        # 1. Borrar mensaje anterior si existe
        if chat_id in config["last_msg_ids"]:
            try:
                await context.bot.delete_message(chat_id, config["last_msg_ids"][chat_id])
            except Exception:
                pass # El mensaje ya fue borrado o expiró

        # 2. Preparar y enviar mensaje
        text = config["welcome_msg"].replace("{MENTION}", mention)
        try:
            sent_msg = await context.bot.send_message(
                chat_id=chat_id, 
                text=text, 
                parse_mode="HTML"
            )
            # 3. Guardar el nuevo ID para la próxima vez
            config["last_msg_ids"][chat_id] = sent_msg.message_id
        except Exception as e:
            logging.error(f"Error enviando bienvenida: {e}")

# --- PANEL DE ADMIN ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.chat.type == "private":
        if user_id not in config["autorizados"]:
            await update.message.reply_text("❌ No tienes acceso. Introduce la contraseña.")
            return
        
        btn = [[InlineKeyboardButton("Configurar Bienvenida 📝", callback_data="set_msg")]]
        await update.message.reply_text(
            f"Panel Admin\nMensaje actual:\n`{config['welcome_msg']}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btn)
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == PASSWORD_CORRECTA:
        config["autorizados"].add(user_id)
        await update.message.reply_text("✅ Acceso concedido. Usa /start para configurar.")
        return

    if user_id in config["autorizados"] and context.user_data.get("state") == "waiting_msg":
        config["welcome_msg"] = text
        context.user_data["state"] = None
        await update.message.reply_text("✅ Mensaje de bienvenida actualizado.")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "set_msg":
        context.user_data["state"] = "waiting_msg"
        await query.edit_message_text("Envíame el nuevo mensaje. Usa `{MENTION}` donde quieras que aparezca el nombre del usuario.")

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(ChatMemberHandler(on_user_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
