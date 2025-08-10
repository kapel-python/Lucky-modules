# meta developer: @Lucky_modules

import random
import time
import asyncio
from datetime import datetime
from .. import loader, utils


@loader.tds
class HackingModule(loader.Module):
    """Модуль для взлома Пентагона"""

    strings = {
        "name": "The hack Pentagon",
    }

    async def hackcmd(self, message):
        """Начать взлом Пентагона"""
        await utils.answer(message, "Начинаю хакерить...")
        user_id = message.sender_id

        start_time = time.time()

        async def update_progress(text, progress, sleep_time):
            await message.edit(text=f"{text} {progress}%")
            await asyncio.sleep(sleep_time)

        current_progress = 0
        await message.edit("Поиск уязвимостей...")

        while current_progress < 100:
            progress_increment = random.randint(10, 20)
            current_progress += progress_increment
            current_progress = min(current_progress, 100)
            await update_progress("Поиск уязвимостей...", current_progress, random.uniform(0.3, 0.5))

        await message.edit("Уязвимости найдены")
        await asyncio.sleep(1)

        current_progress = 0
        await message.edit("Обход системы безопасности...")

        while current_progress < 100:
            progress_increment = random.randint(5, 10)
            current_progress += progress_increment
            current_progress = min(current_progress, 100)
            await update_progress("Обход системы безопасности...", current_progress, random.uniform(0.4, 0.6))

        await message.edit("Система безопасности обойдена")
        await asyncio.sleep(1)

        current_progress = 0
        await message.edit("Получение доступа к данным...")

        while current_progress < 100:
            progress_increment = random.randint(5, 9)
            current_progress += progress_increment
            current_progress = min(current_progress, 100)
            await update_progress("Получение доступа к данным...", current_progress, random.uniform(0.2, 0.4))

        await message.edit("Доступ к данным получен")
        await asyncio.sleep(1)

        current_progress = 0
        await message.edit("Взлом Пентагона...")

        while current_progress < 100:
            progress_increment = 3
            current_progress += progress_increment
            current_progress = min(current_progress, 100)
            await update_progress("Взлом Пентагона...", current_progress, 0.03)

        end_time = time.time()
        elapsed_time = end_time - start_time
        hack_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location = "Вашингтон, США"
        login = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        password = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12))
        access_key = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))
        email = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)) + "@pentagon.gov"
        ip_address = f"192.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        phone_number = "+1 (703) 697-1776"
        device_type = "Windows 10"
        secret_code = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        sender = message.sender if message.sender is not None else await message.get_sender()
        hacker_name = sender.username if (sender and hasattr(sender, "username") and sender.username) else "Неизвестный"

        hack_methods = [
            "SQL Injection (SQL-инъекция)",
            "Cross-Site Scripting (XSS) (Межсайтовый скриптинг)",
            "Remote Code Execution (RCE) (Удаленное выполнение кода)",
            "Buffer Overflow (Переполнение буфера)",
            "Cross-Site Request Forgery (CSRF) (Мошенничество с межсайтовыми запросами)",
            "Directory Traversal (Перемещение по каталогам)",
            "Insecure Direct Object References (IDOR) (Небезопасные прямые ссылки на объекты)",
            "Man-in-the-Middle (MitM) (Атака 'человек посередине')",
            "Credential Stuffing (Заполнение учетных данных)",
            "Session Fixation (Фиксация сессии)",
            "XML External Entity (XXE) Injection (Инъекция внешних сущностей XML)",
            "Clickjacking (Кликджекинг)",
            "Denial of Service (DoS) (Отказ в обслуживании)",
            "Local File Inclusion (LFI) (Включение локальных файлов)",
            "Server-Side Request Forgery (SSRF) (Подделка запросов на стороне сервера)"
        ]

        hack_method = random.choice(hack_methods)
        attempts_count = random.randint(20, 50)

        final_message = (
            f"Пентагон взломан!\n\n"
            f"Логин: {login}\n"
            f"Пароль: {password}\n"
            f"Ключ доступа: {access_key}\n"
            f"Электронная почта: {email}\n"
            f"IP-адрес: {ip_address}\n"
            f"Телефонный номер: {phone_number}\n"
            f"Секретный код доступа: {secret_code}\n"
            f"Дата и время взлома: {hack_time}\n"
            f"Геолокация: {location}\n"
            f"Взлом был с устройства: {device_type}\n"
            f"Взломал: @{hacker_name}\n"
            f"Уязвимость найдена в {hack_method}\n"
            f"Взломан с {attempts_count} попытки\n"
            f"Время взлома: {int(elapsed_time)} секунд"
        )

        await message.edit(final_message)
