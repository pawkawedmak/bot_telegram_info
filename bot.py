import os
import logging
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID", 0))
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")
if not YOUR_USER_ID:
    raise ValueError("YOUR_USER_ID не задан в переменных окружения!")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID не задан в переменных окружения!")

bot = telebot.TeleBot(BOT_TOKEN)

# ─── Проверка владельца ───────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == YOUR_USER_ID

def owner_only(func):
    """Декоратор: только владелец может использовать команду."""
    def wrapper(message):
        if not is_owner(message.from_user.id):
            bot.reply_to(message, "❌ У тебя нет доступа!")
            logger.warning(f"Попытка доступа от user_id={message.from_user.id}")
            return
        return func(message)
    return wrapper

# ─── Команды ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
@owner_only
def help_command(message):
    bot.reply_to(message, (
        "📋 <b>Команды:</b>\n\n"
        "/send &lt;текст&gt; — отправить текст в канал\n"
        "/sendbuttons &lt;текст&gt; — отправить с кнопками (редактируй в коде)\n"
        "/forward — переслать следующее сообщение в канал\n"
        "/photo — отправить следующее фото с подписью в канал\n"
        "/pin — закрепить последнее сообщение канала\n\n"
        "📌 Поддерживается HTML-разметка: <b>жирный</b>, <i>курсив</i>, <code>код</code>"
    ), parse_mode='HTML')


@bot.message_handler(commands=['send'])
@owner_only
def send_to_channel(message):
    text = message.text.partition(' ')[2].strip()
    if not text:
        bot.reply_to(message, "⚠️ Укажи текст: /send Твой текст")
        return
    try:
        bot.send_message(CHANNEL_ID, text, parse_mode='HTML')
        bot.reply_to(message, "✅ Сообщение отправлено!")
        logger.info("Отправлено сообщение в канал")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка отправки: {e}")


@bot.message_handler(commands=['sendbuttons'])
@owner_only
def send_with_buttons(message):
    text = message.text.partition(' ')[2].strip()
    if not text:
        bot.reply_to(message, "⚠️ Укажи текст: /sendbuttons Твой текст")
        return

    # ─── Настрой свои кнопки здесь ───────────────────────────────────────────
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📢 Прямой эфир", url="https://t.me/ссылка1"),
        InlineKeyboardButton("🔵 Наш MAX",     url="https://t.me/ссылка2")
    )
    # ─────────────────────────────────────────────────────────────────────────

    try:
        bot.send_message(CHANNEL_ID, text, reply_markup=markup, parse_mode='HTML')
        bot.reply_to(message, "✅ Сообщение с кнопками отправлено!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка отправки с кнопками: {e}")


@bot.message_handler(commands=['forward'])
@owner_only
def forward_to_channel(message):
    bot.reply_to(message, "📨 Отправь мне сообщение для пересылки в канал:")
    bot.register_next_step_handler(message, process_forward)

def process_forward(message):
    if not is_owner(message.from_user.id):
        return
    try:
        bot.copy_message(CHANNEL_ID, message.chat.id, message.message_id)
        bot.reply_to(message, "✅ Переслано в канал!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка пересылки: {e}")


@bot.message_handler(commands=['photo'])
@owner_only
def send_photo(message):
    bot.reply_to(message, "🖼 Отправь фото (можно с подписью):")
    bot.register_next_step_handler(message, process_photo)

def process_photo(message):
    if not is_owner(message.from_user.id):
        return
    if not message.photo:
        bot.reply_to(message, "⚠️ Это не фото, попробуй ещё раз.")
        return
    try:
        caption = message.caption or ""
        bot.send_photo(CHANNEL_ID, message.photo[-1].file_id, caption=caption, parse_mode='HTML')
        bot.reply_to(message, "✅ Фото отправлено в канал!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка отправки фото: {e}")


@bot.message_handler(commands=['pin'])
@owner_only
def pin_last(message):
    try:
        # Получаем последнее сообщение канала
        channel_info = bot.get_chat(CHANNEL_ID)
        # Закрепляем сообщение по ID (Railway не хранит состояние — передавай ID вручную)
        args = message.text.partition(' ')[2].strip()
        if not args:
            bot.reply_to(message, "⚠️ Укажи ID сообщения: /pin 123")
            return
        bot.pin_chat_message(CHANNEL_ID, int(args), disable_notification=True)
        bot.reply_to(message, "📌 Сообщение закреплено!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка закрепления: {e}")


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Бот запущен...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
