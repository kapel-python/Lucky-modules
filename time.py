# meta developer: @Lucky_modules
# requires: pytz deep_translator geocoder

import pytz
from datetime import datetime
import difflib
import geocoder
from deep_translator import GoogleTranslator
from .. import loader, utils
import asyncio
from concurrent.futures import ThreadPoolExecutor

months_ru = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
weekdays_ru = [
    "понедельник", "вторник", "среда", 
    "четверг", "пятница", "суббота", "воскресенье"
]

def get_utc_offset(tz):
    now = datetime.now(tz)
    offset = now.utcoffset().total_seconds() / 3600
    if offset.is_integer():
        return f"UTC+{int(offset)}" if offset >= 0 else f"UTC{int(offset)}"
    else:
        return f"UTC{offset:+.1f}".replace('+0', '+').replace('-0', '-')

def get_timezone(city):
    try:
        if any(ord(c) > 127 for c in city):
            city_en = GoogleTranslator(source='auto', target='en').translate(city)
        else:
            city_en = city
    except:
        city_en = city
    
    location = geocoder.osm(city)
    if location.ok:
        tz = geocoder.timezone(location.latlng).timezone
        if tz: 
            return tz, location.address
    
    normalized_city = city_en.lower().replace(" ", "_")
    best_match, best_score = None, 0
    for tz in pytz.all_timezones:
        tz_location = tz.split("/")[-1].lower()
        score = difflib.SequenceMatcher(None, normalized_city, tz_location).ratio()
        if score > best_score:
            best_match, best_score = tz, score
    
    return (best_match, best_match) if best_score > 0.5 else (None, None)

def get_time_info(city):
    try:
        timezone, location = get_timezone(city)
        if not timezone:
            return "❌ Часовой пояс не найден"
        
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        utc_offset = get_utc_offset(tz)
        
        return (
            f"📍 Местоположение: {location} ({utc_offset})\n"
            f"🕒 Текущее время: {now.strftime('%H:%M:%S')}\n"
            f"📅 Дата: {now.day} {months_ru[now.month-1]} {now.year}, {weekdays_ru[now.weekday()]}"
        )
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@loader.tds
class TimeMod(loader.Module):
    """Модуль для получения времени"""

    strings = {
        "name": "Time",
        "fetching": "⌛ Запрос времени...",
        "error_city": "🚫 Укажите город (пример: <code>.time Москва</code>). Можно написать с небольшой ошибкой, например <code>.time Mosco</code>",
    }

    async def timecmd(self, message):
        """Получить время по городу. Формат: .time <город>"""
        city = utils.get_args_raw(message)
        if not city:
            await utils.answer(message, self.strings["error_city"])
            return
        
        await utils.answer(message, self.strings["fetching"])
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, get_time_info, city)
            await utils.answer(message, result)
        except Exception as e:
            await utils.answer(message, f"❌ Критическая ошибка: {str(e)}")
