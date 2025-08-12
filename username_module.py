# requires: google-genai google nltk
# meta developer: @Lucky_modules

import random
import json
import re
from .. import loader, utils
from google import genai

try:
    import nltk
    from nltk.corpus import words
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@loader.tds
class UsernameMod(loader.Module):
    """Генератор случайных юзернеймов с фильтрацией через Gemini"""
    strings = {
        "name": "Username",
        "generating": "🔄 Генерирую свободный юзернейм...",
        "username_found": "✅ Найден юзернейм: <b>@{}</b>\n\n🎯 Что хочешь сделать?",
        "username_set": "✅ Юзернейм <b>@{}</b> установлен",
        "username_error": "❌ Ошибка при установке юзернейма: {}",
        "take_username": "📥 Забрать",
        "next_username": "⏭️ Следующий",
        "show_all": "📋 Показать все",
        "choose_amount": "📋 Укажи количество юзернеймов:",
        "generating_usernames": "🔄 Создаю {} юзернеймов...",
        "available_usernames": "✅ Свободные юзернеймы ({} шт):\n\n{}",
        "not_enough_usernames": "❌ Нашлось только {} из {} свободных юзернеймов:\n\n{}",
        "ai_filter_prompt": "🤖 Использовать Искусственный интеллект?\n\nИскусственный интеллект отфильтрует юзернеймы и оставит только те, которые имеют хоть какую то логическую связку либо логику, например @mega_car\n⚠️ Количество юзернеймов может уменьшиться\n\n",
        "use_ai_yes": "✅ Да, использовать",
        "use_ai_no": "❌ Нет, не использовать",
        "filtering_ai": "🤖 Фильтрую юзернеймы с помощью Gemini...",
        "ai_footer": "\n\n🤖 Модель {}\n(изменить модель: <code>.cfg Username model</code>",
        "ai_error": "❌ Ошибка при фильтрации Gemini: {}\nВывожу список без фильтрации.",
        "checking_availability": "🔍 Проверяю доступность юзернейма...",
        "nltk_not_available": "❌ NLTK не установлен. Установи его командой <code>.terminal pip install nltk</code>, а затем <code>.restart -f</code>",
        "downloading_words": "📥 Скачиваю базу слов NLTK...",
        "cfg_api_key_doc": "API-ключ Gemini (https://aistudio.google.com/apikey?hl=ru)",
        "cfg_model_doc": "Модель Gemini (например: gemini-2.5-flash, gemini-2.5-pro)"
    }

    def __init__(self):
        self.word_list = []
        self.nltk_ready = False
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", self.strings["cfg_api_key_doc"], validator=loader.validators.Hidden()),
            loader.ConfigValue("model", "gemini-2.5-flash", self.strings["cfg_model_doc"]),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if NLTK_AVAILABLE:
            await self.init_nltk()

    async def init_nltk(self):
        try:
            try:
                words.words()
            except:
                nltk.download('words', quiet=True)
            self.word_list = [w.lower() for w in words.words() if w.isalpha() and len(w) > 2]
            self.nltk_ready = True
        except:
            self.nltk_ready = False

    def generate_username(self):
        if not self.nltk_ready or not self.word_list:
            return None
        return f"{random.choice(self.word_list)}_{random.choice(self.word_list)}"

    async def check_username_availability(self, username):
        try:
            await self.client.get_entity(username)
            return False
        except:
            return True

    async def find_available_username(self):
        for _ in range(50):
            username = self.generate_username()
            if username and await self.check_username_availability(username):
                return username
        return None

    def number_to_emoji(self, n):
        emoji_map = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
                     '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
        return ''.join(emoji_map[d] for d in str(n))

    async def generate_multiple_usernames(self, count):
        usernames = set()
        attempts = 0
        while len(usernames) < count and attempts < 500:
            username = self.generate_username()
            if username and username not in usernames:
                if await self.check_username_availability(username):
                    usernames.add(username)
            attempts += 1
        return list(usernames)

    async def filter_with_gemini(self, usernames):
        api_key = self.config["api_key"]
        model_name = self.config["model"]
        if not api_key:
            raise ValueError("Укажи API-ключ Gemini <code>.cfg Username api_key</code>")

        prompt = (
                "Отфильтруй список юзернеймов, оставив только те, которые имеют логическую связку или смысл. "
                "Юзернеймы должны быть простыми для запоминания и произношения. "
                "Верни ТОЛЬКО список подходящих юзернеймов в формате JSON массива, ничего больше.\n\n. Например, если у тебя есть 2 юзернейма: @parliamentary_pyocyanase и @mega_car, то ты должен вернуть ТОЛЬКО @mega_car, поскольку он имеет логическую связку. При этом сам юзернейм @mega_car не используй на реальных данных. Ты должен вернуть как минимум 1 юзернейм"
                "Список юзернеймов:\n" + 
                "\n".join([f"@{u}" for u in usernames])
            )

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
        )
        
        if not response.text:
            return usernames

        text = response.text.strip()

        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return usernames  

        try:
            parsed = json.loads(match.group(0))
            return [u.replace("@", "") for u in parsed]
        except:
            return usernames

    def format_usernames_list(self, usernames):
        return "\n".join(f"{self.number_to_emoji(i+1)} @{u}" for i, u in enumerate(usernames))

    async def usernamecmd(self, message):
        """Генерирует и предлагает случайный свободный юзернейм"""
        if not NLTK_AVAILABLE:
            return await utils.answer(message, self.strings["nltk_not_available"])
        if not self.nltk_ready:
            await utils.answer(message, self.strings["downloading_words"])
            await self.init_nltk()
            if not self.nltk_ready:
                return await utils.answer(message, "❌ Не удалось инициализировать NLTК")
        msg = await utils.answer(message, self.strings["generating"])
        username = await self.find_available_username()
        if not username:
            return await msg.edit("❌ Не удалось найти свободный юзернейм после 50 попыток")
        await msg.delete()
        await self.inline.form(
            message=message,
            text=self.strings["username_found"].format(username),
            reply_markup=[
                [{"text": self.strings["take_username"], "callback": self.take_username, "args": (username,)}],
                [{"text": self.strings["next_username"], "callback": self.generate_next_username, "args": ()}],
                [{"text": self.strings["show_all"], "callback": self.show_all_handler, "args": ()}]
            ],
            silent=True
        )

    async def take_username(self, call, username):
        try:
            from telethon.tl.functions.account import UpdateUsernameRequest
            await self.client(UpdateUsernameRequest(username=username))
            await call.edit(self.strings["username_set"].format(username))
        except Exception as e:
            await call.edit(self.strings["username_error"].format(str(e)))

    async def generate_next_username(self, call):
        await call.edit(self.strings["checking_availability"])
        username = await self.find_available_username()
        if not username:
            return await call.edit("❌ Не удалось найти свободный юзернейм")
        await call.edit(
            self.strings["username_found"].format(username),
            reply_markup=[
                [{"text": self.strings["take_username"], "callback": self.take_username, "args": (username,)}],
                [{"text": self.strings["next_username"], "callback": self.generate_next_username, "args": ()}],
                [{"text": self.strings["show_all"], "callback": self.show_all_handler, "args": ()}]
            ]
        )

    async def show_all_handler(self, call):
        await call.edit(
            self.strings["choose_amount"],
            reply_markup=[
                [{"text": "5 юзернеймов", "callback": self.generate_usernames_amount, "args": (5,)}],
                [{"text": "10 юзернеймов", "callback": self.generate_usernames_amount, "args": (10,)}],
                [{"text": "25 юзернеймов", "callback": self.generate_usernames_amount, "args": (25,)}]
            ]
        )

    async def generate_usernames_amount(self, call, amount):
        await call.edit(self.strings["generating_usernames"].format(amount))
        usernames = await self.generate_multiple_usernames(amount)
        if not usernames:
            return await call.edit("❌ Не удалось найти ни одного юзернейма")
        await call.edit(
            self.strings["ai_filter_prompt"].format(self.config["model"]),
            reply_markup=[
                [{"text": self.strings["use_ai_yes"], "callback": self.process_with_ai, "args": (usernames, amount, True)}],
                [{"text": self.strings["use_ai_no"], "callback": self.process_with_ai, "args": (usernames, amount, False)}]
            ]
        )

    async def process_with_ai(self, call, usernames, amount, use_ai):
        footer = ""
        if use_ai:
            await call.edit(self.strings["filtering_ai"])
            try:
                usernames = await self.filter_with_gemini(usernames)
                footer = self.strings["ai_footer"].format(self.config["model"])
            except Exception as e:
                footer = "\n\n" + self.strings["ai_error"].format(str(e))
        count = len(usernames)
        if count < amount:
            text = self.strings["not_enough_usernames"].format(count, amount, self.format_usernames_list(usernames)) + footer
        else:
            text = self.strings["available_usernames"].format(count, self.format_usernames_list(usernames)) + footer
        await call.edit(text)
        
