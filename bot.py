import os
import logging
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# ================= БЕЗОПАСНЫЕ НАСТРОЙКИ ДЛЯ СЕРВЕРА =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# ====================================================================

SYSTEM_INSTRUCTION = """
Ты — умный ИИ-ассистент для автоматизации рутинных задач пользователя.
Твоя цель: помогать планировать день, структурировать хаотичные мысли в списки задач, 
выделять главное из текстов, писать короткие ответы на письма и напоминать о важном.
Отвечай четко, структурированно, без лишней «воды». Используй списки и форматирование.
"""

client = genai.Client(api_key=GEMINI_API_KEY)
user_chats = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_chats[user_id] = client.chats.create(
        model="gemini-1.5-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
    )
    await update.message.reply_text(
        "👋 Привет! Я твой Gemini-агент для рутины, запущенный на сервере Render!\n\n"
        "Отправь мне задачу, список дел или просто задай вопрос!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if user_id not in user_chats:
        user_chats[user_id] = client.chats.create(
            model="gemini-1.5-flash",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        chat_session = user_chats[user_id]
        response = chat_session.send_message(user_text)
        await update.message.reply_text(response.text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini: {e}")
        await update.message.reply_text("Извини, произошла ошибка при обработке запроса. Попробуй еще раз.")

# Функция для обмана Render: создает фейковый веб-сайт, который слушает порт хостинга
def run_fake_web_server():
    port = int(os.getenv("PORT", 10000))
    server_address = ("", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Фейковый веб-сервер успешно запущен на порту {port}")
    httpd.serve_forever()

def main() -> None:
    # Запускаем веб-сервер в отдельном фоновом потоке, чтобы он не мешал боту
    web_thread = threading.Thread(target=run_fake_web_server, daemon=True)
    web_thread.start()

    # Запускаем Telegram бота
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот успешно запущен в связке с веб-портом и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    main()
