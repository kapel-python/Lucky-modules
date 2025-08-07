# meta developer: @Lucky_modules

from .. import loader, utils
import random
import aiohttp
import asyncio
import json

try:
    import nltk
    from nltk.corpus import words
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

@loader.tds
class UsernameMod(loader.Module):
    """Генератор случайных юзернеймов"""
    strings = {
        "name": "Username",
        "generating": "🔄 Генерирую свободный юзернейм...",
        "username_found": "✅ Найден свободный юзернейм: <b>@{}</b>\n\n🎯 Что хочешь сделать?",
        "username_set": "✅ Юзернейм <b>@{}</b> установлен!",
        "username_error": "❌ Ошибка при установке юзернейма: {}",
        "take_username": "📥 Забрать",
        "next_username": "⏭️ Следующий",
        "show_all": "📋 Показать все",
        "choose_amount": "📋 Укажи количество юзернеймов:",
        "generating_usernames": "🔄 Создаю {} юзернеймов...",
        "available_usernames": "✅ Свободные юзернеймы ({} шт):\n\n{}",
        "not_enough_usernames": "❌ Нашлось только {} из {} свободных юзернеймов (скорее всего их отфильтровал ИИ):\n\n{}",
        "ai_filter_prompt": "🤖 Использовать Искусственный интеллект?\n\nИскусственный интеллект отфильтрует юзернеймы и оставит только те, которые имеют хоть какую то логическую связку либо логику, например @mega_car\n⚠️ Количество юзернеймов может уменьшиться\n\n<i>Этот модуль не предназначен для массового использования, поэтому баланс сервиса API ограничен, следи и не трать много, ведь он используется всеми пользователями этого модуля</i>\n\n💸 Текущий баланс API сервиса: {}\n🤖 Модель ИИ: {}",
        "use_ai_yes": "✅ Да, использовать",
        "use_ai_no": "❌ Нет, не использовать",
        "filtering_ai": "🤖 Фильтрую юзернеймы с помощью ИИ...",
        "ai_footer": "\n\n🤖 Для фильтрации юзернеймов использовалась ИИ ({})",
        "ai_error": "❌ Ошибка при фильтрации ИИ: {}\nВывожу список без фильтрации.",
        "checking_availability": "🔍 Проверяю доступность юзернейма...",
        "nltk_not_available": "❌ NLTK не установлен. Установи его командой <code>.terminal pip install nltk</code>, а затем <code>.restart -f</code>",
        "downloading_words": "📥 Скачиваю базу слов NLTK...",
    }

    API_KEY = "shds-wFfXMK5v8V54znYAdmBVQ67JJaY"
    API_CHAT_URL = "https://gptunnel.ru/v1/chat/completions"
    API_BALANCE_URL = "https://gptunnel.ru/v1/balance"
    MODEL = "gpt-4.1-nano"

    def __init__(self):
        self.word_list = []
        self.nltk_ready = False

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
        except Exception as e:
            self.nltk_ready = False

    def generate_username(self):
        if not self.nltk_ready or not self.word_list:
            return None
        
        word1 = random.choice(self.word_list)
        word2 = random.choice(self.word_list)
        return f"{word1}_{word2}"

    async def check_username_availability(self, username):
        try:
            entity = await self.client.get_entity(username)
            return False  # Юзернейм занят
        except Exception:
            return True  # Юзернейм свободен

    async def find_available_username(self):
        max_attempts = 50
        for _ in range(max_attempts):
            username = self.generate_username()
            if username and await self.check_username_availability(username):
                return username
        return None

    def number_to_emoji(self, n):
        emoji_map = {
            '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
            '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
        }
        return ''.join(emoji_map[d] for d in str(n))

    async def generate_multiple_usernames(self, count, max_attempts=500):
        usernames = set()
        attempts = 0
        
        while len(usernames) < count and attempts < max_attempts:
            username = self.generate_username()
            if username and username not in usernames:
                if await self.check_username_availability(username):
                    usernames.add(username)
            attempts += 1
        
        return list(usernames)

    async def get_ai_balance(self):
        headers = {"Authorization": self.API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_BALANCE_URL, headers=headers, params={"useWalletBalance": "true"}) as response:
                response.raise_for_status()
                data = await response.json()
                return float(data.get("balance", 0))

    async def filter_with_ai(self, usernames):
        try:
            balance_before = await self.get_ai_balance()
            
            prompt = (
                "Отфильтруй список юзернеймов, оставив только те, которые имеют логическую связку или смысл. "
                "Юзернеймы должны быть простыми для запоминания и произношения. "
                "Верни ТОЛЬКО список подходящих юзернеймов в формате JSON массива, ничего больше.\n\n. Например, если у тебя есть 2 юзернейма: @parliamentary_pyocyanase и @mega_car, то ты должен вернуть ТОЛЬКО @mega_car, поскольку он имеет логическую связку. При этом сам юзернейм @mega_car не используй на реальных данных."
                "Список юзернеймов:\n" + 
                "\n".join([f"@{u}" for u in usernames])
            )
            
            headers = {
                "Authorization": self.API_KEY,
                "Content-Type": "application/json"
            }
            data = {
                "model": self.MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "useWalletBalance": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_CHAT_URL, json=data, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    ai_response = result["choices"][0]["message"]["content"]
            
            filtered = json.loads(ai_response)
            
            return [u.replace("@", "") for u in filtered], balance_before
        
        except Exception as e:
            
            return usernames, 0

    def format_usernames_list(self, usernames):
        return "\n".join(
            f"{self.number_to_emoji(i+1)} @{username}"
            for i, username in enumerate(usernames)
        )

    async def usernamecmd(self, message):
        """Генерирует и предлагает случайный свободный юзернейм"""
        if not NLTK_AVAILABLE:
            await utils.answer(message, self.strings["nltk_not_available"])
            return

        if not self.nltk_ready:
            await utils.answer(message, self.strings["downloading_words"])
            await self.init_nltk()
            if not self.nltk_ready:
                await utils.answer(message, "❌ Не удалось инициализировать NLTК")
                return

        msg = await utils.answer(message, self.strings["generating"])
        username = await self.find_available_username()
        
        if not username:
            await msg.edit("❌ Не удалось найти свободный юзернейм после 50 попыток")
            return

        await msg.delete()
        
        await self.inline.form(
            message=message,
            text=self.strings["username_found"].format(username),
            reply_markup=[
                [{
                    "text": self.strings["take_username"],
                    "callback": self.take_username,
                    "args": (username,)
                }],
                [{
                    "text": self.strings["next_username"], 
                    "callback": self.generate_next_username,
                    "args": ()
                }],
                [{
                    "text": self.strings["show_all"],
                    "callback": self.show_all_handler,
                    "args": ()
                }]
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
            await call.edit("❌ Не удалось найти свободный юзернейм")
            return

        await call.edit(
            self.strings["username_found"].format(username),
            reply_markup=[
                [{
                    "text": self.strings["take_username"],
                    "callback": self.take_username,
                    "args": (username,)
                }],
                [{
                    "text": self.strings["next_username"],
                    "callback": self.generate_next_username, 
                    "args": ()
                }],
                [{
                    "text": self.strings["show_all"],
                    "callback": self.show_all_handler,
                    "args": ()
                }]
            ]
        )

    async def show_all_handler(self, call):
        await call.edit(
            self.strings["choose_amount"],
            reply_markup=[
                [{
                    "text": "5 юзернеймов",
                    "callback": self.generate_usernames_amount,
                    "args": (5,)
                }],
                [{
                    "text": "10 юзернеймов",
                    "callback": self.generate_usernames_amount,
                    "args": (10,)
                }],
                [{
                    "text": "25 юзернеймов",
                    "callback": self.generate_usernames_amount,
                    "args": (25,)
                }]
            ]
        )

    async def generate_usernames_amount(self, call, amount):
        await call.edit(self.strings["generating_usernames"].format(amount))
        usernames = await self.generate_multiple_usernames(amount)
        
        if not usernames:
            await call.edit("❌ Не удалось найти ни одного юзернейма")
            return
        try:
            balance = await self.get_ai_balance()
            balance_str = "{:.2f}₽".format(balance)
        except:
            balance = 0.0
            
        await call.edit(
            self.strings["ai_filter_prompt"].format(balance_str, self.MODEL),
            reply_markup=[
                [{
                    "text": self.strings["use_ai_yes"],
                    "callback": self.process_with_ai,
                    "args": (usernames, amount, True)
                }],
                [{
                    "text": self.strings["use_ai_no"],
                    "callback": self.process_with_ai,
                    "args": (usernames, amount, False)
                }]
            ]
        )
        
    def format_cost(self, cost):
        if cost < 0.01:
            return "потрачено меньше 0.01₽ либо ИИ ничего не отфильтровал"
        return f"потрачено {cost:.2f}₽"
    
    
    async def process_with_ai(self, call, usernames, amount, use_ai):
        ai_cost = 0.0
        footer = ""
        
        if use_ai:
            await call.edit(self.strings["filtering_ai"])
            try:
                
                filtered_usernames, balance_before = await self.filter_with_ai(usernames)
                balance_after = await self.get_ai_balance()
                ai_cost = balance_before - balance_after
                
                usernames = filtered_usernames
                footer = self.strings["ai_footer"].format(self.format_cost(ai_cost))
                
            except Exception as e:
                footer = "\n\n" + self.strings["ai_error"].format(str(e))
        
        count = len(usernames)
        if count < amount:
            text = self.strings["not_enough_usernames"].format(
                count, 
                amount,
                self.format_usernames_list(usernames)
            ) + footer
        else:
            text = self.strings["available_usernames"].format(
                count,
                self.format_usernames_list(usernames)
            ) + footer
        
        await call.edit(text)
