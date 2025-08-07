import aiohttp
import datetime
from urllib.parse import quote
from .. import loader, utils
"""Модуль создан @Droplucky_project"""

def weather_code_to_text(code):
    codes = {
        0: "Ясно ☀️",
        1: "Преимущественно ясно 🌤️",
        2: "Переменная облачность ⛅",
        3: "Пасмурно ☁️",
        45: "Туман 🌫️",
        48: "Туман с инеем 🌫️",
        51: "Легкая морось 🌧️",
        53: "Морось 🌧️",
        55: "Сильная морось 🌧️",
        56: "Ледяная морось 🌧️❄️",
        57: "Сильная ледяная морось 🌧️❄️",
        61: "Небольшой дождь 🌦️",
        63: "Умеренный дождь 🌧️",
        65: "Сильный дождь 🌧️💨",
        66: "Ледяной дождь 🌧️❄️",
        67: "Сильный ледяной дождь 🌧️❄️💨",
        71: "Небольшой снег ❄️",
        73: "Умеренный снег ❄️❄️",
        75: "Сильный снег ❄️❄️❄️",
        77: "Снежные зерна ❄️",
        80: "Небольшой ливень 🌦️",
        81: "Умеренный ливень 🌧️",
        82: "Сильный ливень 🌧️💨",
        85: "Небольшой снегопад ❄️🌨️",
        86: "Сильный снегопад ❄️❄️🌨️",
        95: "Гроза ⛈️",
        96: "Гроза с градом ⛈️🧊",
        99: "Сильная гроза с градом ⛈️🧊💨"
    }
    return codes.get(code, "Неизвестно")

def get_aqi_description(aqi):
    if aqi <= 20:
        return "💚 Отличное качество воздуха! Идеальный день для прогулок!"
    elif aqi <= 40:
        return "💛 Хорошее качество воздуха. Можно смело планировать активный день!"
    elif aqi <= 60:
        return "🟡 Удовлетворительное качество. Для большинства людей безопасно."
    elif aqi <= 80:
        return "🧡 Среднее качество. Люди с чувствительностью могут испытывать дискомфорт."
    elif aqi <= 100:
        return "❤️ Плохое качество. Рекомендуется ограничить время на улице."
    else:
        return "💔 Опасное качество воздуха! Избегайте длительного пребывания на улице!"

def format_date(date_str):
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    return f"{date_obj.strftime('%d.%m.%Y')}, {days[date_obj.weekday()]}"

def format_time(time_str):
    return time_str.split('T')[1][:5] if 'T' in time_str else time_str[:5]

@loader.tds
class WeatherModule(loader.Module):
    """Модуль для получения подробного прогноза погоды"""

    strings = {
        "name": "Weather",
        "error": "❌ Ошибка при получении данных о погоде: {}",
        "no_city": "⚠️ Введи название города после команды .weather, например <code>.weather Москва</code>",
        "city_not_found": "❌ Информация о погоде в городе {city} недоступна",
        "processing": "⏳ Получение данных о погоде...",
    }

    async def weathercmd(self, message):
        "После команды пиши город"
        processing = await utils.answer(message, self.strings["processing"])
        
        try:
            city = utils.get_args_raw(message)
            if not city:
                try:
                    await processing.edit(self.strings["no_city"])
                except:
                    msg = await processing.client.send_message(
                        processing.chat_id,
                        self.strings["no_city"],
                        reply_to=message.id
                    )
                    await processing.delete()
                return

            async with aiohttp.ClientSession() as session:
                url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(city)}"
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    data = await response.json()
                    if not data:
                        try:
                            await processing.edit(self.strings["city_not_found"].format(city=city))
                        except:
                            msg = await processing.client.send_message(
                                processing.chat_id,
                                self.strings["city_not_found"].format(city=city),
                                reply_to=message.id
                            )
                            await processing.delete()
                        return
                    first_result = data[0]
                    lat = float(first_result['lat'])
                    lon = float(first_result['lon'])
                    canonical_city = first_result.get('display_name', city).split(',')[0].title()

                base_url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    'latitude': str(lat),
                    'longitude': str(lon),
                    'hourly': 'temperature_2m,apparent_temperature,weathercode,relativehumidity_2m',
                    'daily': 'weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,windspeed_10m_max',
                    'current_weather': 'true',
                    'timezone': 'auto',
                    'forecast_days': '7'
                }
                async with session.get(base_url, params=params) as response:
                    weather_data = await response.json()
                
                aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
                aqi_params = {
                    'latitude': str(lat),
                    'longitude': str(lon),
                    'current': 'european_aqi',
                    'forecast_days': '0'
                }
                async with session.get(aqi_url, params=aqi_params) as response:
                    aqi_data = await response.json()
            
            current = weather_data['current_weather']
            hourly = weather_data['hourly']
            daily = weather_data['daily']
            
            current_time = datetime.datetime.fromisoformat(current['time'])
            current_hour = current_time.hour
            
            weather_message = (
                f"🌍 Сейчас в {canonical_city}: {current['temperature']}°C\n"
                f"🌬️ Ощущается как: {hourly['apparent_temperature'][current_hour]}°C\n"
                f"💨 Ветер: {current['windspeed']} км/ч\n"
                f"💧 Влажность: {hourly['relativehumidity_2m'][current_hour]}%\n"
            )
            
            aqi = aqi_data.get('current', {}).get('european_aqi')
            if aqi:
                aqi_desc = get_aqi_description(aqi)
                weather_message += f"🌫️ ИКВ (индекс качества воздуха): {aqi} - {aqi_desc}\n"
            
            weather_message += f"☁️ Состояние: {weather_code_to_text(current['weathercode'])}\n\n"
            
            days_ru = {1: "Завтра", 2: "Послезавтра"}
            
            for i in range(1, len(daily['time'])):
                date_str = daily['time'][i]
                date_formatted = format_date(date_str)
                
                if i in (1, 2):
                    title = f"📅 {days_ru[i]} ({date_formatted})"
                else:
                    title = f"📅 {date_formatted}"
                
                day_weather = (
                    f"{title}\n"
                    f"🌡️ Температура: {daily['temperature_2m_max'][i]}°C / {daily['temperature_2m_min'][i]}°C\n"
                    f"🌬️ Ощущается как: {daily['apparent_temperature_max'][i]}°C\n"
                    f"💨 Ветер: {daily['windspeed_10m_max'][i]} км/ч\n"
                    f"☁️ Состояние: {weather_code_to_text(daily['weathercode'][i])}\n"
                )
                weather_message += f"\n{day_weather}"
            
            if daily['sunrise'] and daily['sunset']:
                sunrise = format_time(daily['sunrise'][0])
                sunset = format_time(daily['sunset'][0])
                weather_message += (
                    f"\n🌅 Восход: {sunrise}\n"
                    f"🌇 Закат: {sunset}\n\n⛅ Данные получены без API ключей из открытых источников"
                )
            
            try:
                await processing.edit(weather_message)
            except:
                try:
                    msg = await processing.client.send_message(
                        processing.chat_id,
                        weather_message,
                        reply_to=message.id
                    )
                except:
                    msg = await processing.client.send_message(
                        processing.chat_id,
                        weather_message
                    )
                await processing.delete()
            
        except Exception as e:
            try:
                await processing.edit(self.strings["error"].format(str(e)))
            except:
                msg = await processing.client.send_message(
                    processing.chat_id,
                    self.strings["error"].format(str(e)),
                    reply_to=message.id
                )
                await processing.delete()
