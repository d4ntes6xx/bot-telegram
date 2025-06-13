import telebot
import requests
import asyncio
import pycountry
from deep_translator import GoogleTranslator
#from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

#https://home.openweathermap.org/users/sign_in

# Ключевые слова и ответы
keywords = {
    "привет": "Привет! Как дела?",
    "как дела": "У меня всё отлично! А у вас?",
    "погода": "Сегодня прекрасная погода!"
}

TOKEN = ""
WEATHER_API_KEY = "7245b2b069eefb40ff7d56020cfa1cab"
CREATOR_ID = ""
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

user_messages = {}

def translate_city_to_english(city):
    """Переводит название города на английский (синхронно)"""
    translated = GoogleTranslator(source="auto", target="en").translate(city)
    return translated
def translate_to_russian(city):
    """Переводит текст с английского на русский"""
    perevod = GoogleTranslator(source="en", target="ru").translate(city)
    return perevod

def get_country_name(country_code):
    """Преобразует код страны (ISO 3166-1) в полное название"""
    country = pycountry.countries.get(alpha_2=country_code)
    return country.name if country else "Страна не найдена"

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "<b>Привет! Я предложка-бот @arbuzinskiedvizheniya.</b>\nЕсли имеются вопросы/идеи - задавай в чат.\n", parse_mode="HTML")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "<b>Список доступных команд:</b>\n\n"
                          "<b>/start</b> - Старт бота.\n"
                          "<b>/help</b> - Помощь по использованию бота.\n"
                          "<b>/weather</b> - Погода в вашем городе.\n"
                          "<b>/contact</b> - Связаться с Данте.\n"
                          "<i>Если хотите узнать погоду - отвечайте именно на <b>сообщение с запросом на город</b>.</i>", parse_mode="HTML")

@bot.message_handler(commands=['contact'])
def send_contact_info(message):
    bot.reply_to(message, "<b>Связь с создателем:</b>\n\n"
                          "Если у вас есть вопросы или предложения, свяжитесь с ним через меня.", parse_mode="HTML")
    bot.register_next_step_handler(send_contact_info, forward_message)

def get_weather(city):
    """Запрашивает погоду в OpenWeather API"""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    print(f"Запрашиваем URL: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        country_code = data["sys"]["country"]
        country_name = get_country_name(country_code)
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]

        return (
            f"Погода в {translate_to_russian(city)}\n"
            f"🌍 {translate_to_russian(city)}, {translate_to_russian(country_name)} (координаты: {lat}, {lon})\n"
            f"☁️ Погода: {weather_desc.capitalize()}\n"
            f"🌡 Температура: {temp}°C\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind_speed} м/с"
        )
    return "❌ Не удалось получить погоду."


@bot.message_handler(commands=["weather"])
def ask_city(message):
    bot.reply_to(message, "Введите название города!")


@bot.message_handler(
    func=lambda message: message.reply_to_message and message.reply_to_message.text == "Введите название города!")
def handle_city(message):
    city = message.text.strip()
    city_translated = translate_city_to_english(city)
    weather_info = get_weather(f"{city_translated}")
    bot.reply_to(message, weather_info)


@bot.message_handler(content_types=['text', 'photo', 'audio', 'document', 'video', 'voice', 'sticker', 'animation'])
def forward_message(message):
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
    
    mesfrom = f"Сообщение от {user_link}:"

    text_to_creator = mesfrom

    sent_message = bot.send_message(CREATOR_ID, text_to_creator, parse_mode="HTML")
    forwarded_message = bot.forward_message(CREATOR_ID, message.chat.id, message.message_id)
    
    user_messages[sent_message.message_id] = user_id
    user_messages[forwarded_message.message_id] = user_id

    print(f"Сохранён ID: {sent_message.message_id} и {forwarded_message.message_id} для пользователя {user_id}")

    bot.send_message(message.chat.id, "✅ Ваше сообщение успешно отправлено!")
    
    #msg = bot.send_message(CREATOR_ID, "✉️ Напишите ответ пользователю:")
    #bot.register_next_step_handler(msg, reply_to_user, sent_message.message_id)

    
#здесь я пытался сделать функцию отвеетить через "/ответить {текст}"
@bot.message_handler(commands=['ответить'])
def reply_to_user(message): #, original_message_id=None
    print(f"Получена команда /ответить от {message.chat.id}")
    
    original_message = message.reply_to_message
    user_id = user_messages.get(original_message.message_id)

    if message.chat.id != int(CREATOR_ID):
        bot.send_message(message.chat.id, "⚠️ Ошибка: у вас нет доступа к этой команде.")
        return

    if not message.reply_to_message or not message.reply_to_message.text.startswith("Сообщение от"):
        print("Ошибка: reply_to_message отсутствует или неверный формат")
        bot.send_message(CREATOR_ID, "⚠️ Ошибка: нужно отвечать на сообщение, содержащее 'Сообщение от {пользователь}:'.")
        return

    if original_message_id is None:
        bot.send_message(CREATOR_ID, "⚠️ Ошибка: ID сообщения не передан.")
        return

    if not user_id:
        bot.send_message(CREATOR_ID, "⚠️ Ошибка: невозможно определить получателя.")
        return  

        command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Ошибка: после /ответить нужно написать текст ответа.")
        return

    print(f"Ответ на сообщение ID: {original_message_id}, получатель: {user_id}")

    '''
    if user_id:
        reply_text = message.text.split(maxsplit=1)[1]
        bot.send_message(user_id, f"✉️ Ответ от Данте: {reply_text}", parse_mode="HTML")
        bot.send_message(CREATOR_ID, "✅ Ответ успешно отправлен!")
    else:
        bot.send_message(CREATOR_ID, "⚠️ Ошибка: невозможно определить получателя.")
    '''

    
    reply_text = command_parts[1]
    print(f"Ответ на сообщение ID: {original_message.message_id}, получатель: {user_id}")

    try:
        bot.send_message(user_id, f"✉️ Ответ от Данте: {reply_text}", parse_mode="HTML")
        bot.send_message(CREATOR_ID, "✅ Ответ успешно отправлен!")
    except Exception as e:
        bot.send_message(CREATOR_ID, f"⚠️ Ошибка при отправке ответа: {str(e)}")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.polling(none_stop=True)