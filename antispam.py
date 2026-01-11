# meta developer: @Lucky_modules

__version__ = (1, 2, 0)

from .. import loader, utils
import time

class AntiSpamModule(loader.Module):
    """Модуль для защиты от спама в чатах"""
    strings = {"name": "AntiSpam"}

    def __init__(self):
        self.cache = {}
        self.chat_settings = {}
        self.whitelist = set()

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.chat_settings = self.db.get("antispam", "chat_settings", {})
        self.whitelist = set(self.db.get("antispam", "whitelist", []))

    async def antispamchatcmd(self, message):
        """Добавить/удалить чат для антиспама"""
        if message.chat is None:
            await message.edit("🚫 Эта команда доступна только в чатах")
            return
        
        chat_id = str(message.chat.id)
        if chat_id in self.chat_settings:
            del self.chat_settings[chat_id]
            await message.edit("✅ Чат удалён из антиспама")
        else:
            self.chat_settings[chat_id] = {
                "enabled": False,
                "time_limit": 1.0
            }
            await message.edit("✅ Чат добавлен в антиспам")
        
        self.db.set("antispam", "chat_settings", self.chat_settings)

    async def antispamcmd(self, message):
        """Включить/отключить антиспам"""
        if message.chat is None:
            await message.edit("🚫 Эта команда доступна только в чатах")
            return
        
        chat_id = str(message.chat.id)
        if chat_id not in self.chat_settings:
            await message.edit("⚠️ Чат не добавлен. Используй .antispamchat")
            return
        
        self.chat_settings[chat_id]["enabled"] ^= True
        status = "включён" if self.chat_settings[chat_id]["enabled"] else "выключен"
        await message.edit(f"✅ Антиспам {status}.")
        self.db.set("antispam", "chat_settings", self.chat_settings)

    async def antispamtimecmd(self, message):
        """Изменить время для антиспама (в секундах)"""
        if message.chat is None:
            await message.edit("🚫 Эта команда доступна только в чатах")
            return
        
        chat_id = str(message.chat.id)
        
        if chat_id not in self.chat_settings:
            await message.edit("⚠️ Чат не добавлен. Используй .antispamchat")
            return
        
        args = utils.get_args_raw(message)
        
        if not args:
            current_limit = self.chat_settings[chat_id]["time_limit"]
            await message.edit(
                f"🕒 Текущий лимит антиспама: {current_limit} секунд\n"
                "📝 Введите новое значение через команду: "
                f".antispamtime <число>"
            )
            return
        
        try:
            time_limit = float(args)
            if time_limit <= 0:
                raise ValueError
                
            self.chat_settings[chat_id]["time_limit"] = time_limit
            self.db.set("antispam", "chat_settings", self.chat_settings)
            await message.edit(f"✅ Лимит установлен: {time_limit} сек.")
            
        except (ValueError, TypeError):
            await message.edit("❌ Некорректное значение. Используй число больше 0 (например: 0.7)")

    async def antispamstatuscmd(self, message):
        """Показать статус антиспама в текущем чате"""
        if message.chat is None:
            await message.edit("🚫 Эта команда доступна только в чатах")
            return
        
        chat_id = str(message.chat.id)
        
        if chat_id not in self.chat_settings:
            await message.edit("⚠️ Чат не добавлен в антиспам. Используй .antispamchat")
            return
        
        settings = self.chat_settings[chat_id]
        status = "✅ Включён" if settings["enabled"] else "❌ Выключен"
        whitelist_count = len(self.whitelist)
        
        await message.edit(
            f"📊 <b>Статус антиспама:</b>\n"
            f"├ Состояние: {status}\n"
            f"├ Лимит времени: {settings['time_limit']} сек.\n"
            f"└ В белом списке: {whitelist_count} польз."
        )

    async def antispamaddcmd(self, message):
        """Добавить пользователя в белый список (ответь на сообщение или укажи ID)"""
        args = utils.get_args_raw(message)
        user_id = None
        
        if message.is_reply:
            reply = await message.get_reply_message()
            user_id = reply.sender_id
        
        elif args:
            try:
                user_id = int(args)
            except ValueError:
                await message.edit("❌ Неверный ID пользователя")
                return
        else:
            await message.edit("⚠️ Ответь на сообщение пользователя или укажи его ID")
            return
        
        if user_id in self.whitelist:
            await message.edit("⚠️ Пользователь уже в белом списке")
            return
        
        self.whitelist.add(user_id)
        self.db.set("antispam", "whitelist", list(self.whitelist))
        
        try:
            user = await self.client.get_entity(user_id)
            name = user.first_name or "Пользователь"
            await message.edit(f"✅ <b>{name}</b> добавлен в белый список")
        except:
            await message.edit(f"✅ Пользователь <code>{user_id}</code> добавлен в белый список")

    async def antispamdelcmd(self, message):
        """Удалить пользователя из белого списка (ответь на сообщение или укажи ID)"""
        args = utils.get_args_raw(message)
        user_id = None
        
        if message.is_reply:
            reply = await message.get_reply_message()
            user_id = reply.sender_id
        elif args:
            try:
                user_id = int(args)
            except ValueError:
                await message.edit("❌ Неверный ID пользователя")
                return
        else:
            await message.edit("⚠️ Ответь на сообщение пользователя или укажи его ID")
            return
        
        if user_id not in self.whitelist:
            await message.edit("⚠️ Пользователя нет в белом списке")
            return
        
        self.whitelist.remove(user_id)
        self.db.set("antispam", "whitelist", list(self.whitelist))
        
        try:
            user = await self.client.get_entity(user_id)
            name = user.first_name or "Пользователь"
            await message.edit(f"✅ <b>{name}</b> удалён из белого списка")
        except:
            await message.edit(f"✅ Пользователь <code>{user_id}</code> удалён из белого списка")

    async def antispamlistcmd(self, message):
        """Показать список пользователей в белом списке"""
        if not self.whitelist:
            await message.edit("📋 Белый список пуст")
            return
        
        text = "📋 <b>Белый список антиспама:</b>\n\n"
        
        for user_id in self.whitelist:
            try:
                user = await self.client.get_entity(user_id)
                name = user.first_name or "Неизвестно"
                username = f"@{user.username}" if user.username else ""
                text += f"├ <b>{name}</b> {username} (<code>{user_id}</code>)\n"
            except:
                text += f"├ <code>{user_id}</code>\n"
        
        text = text.rstrip("\n") + "\n└ Всего: " + str(len(self.whitelist))
        await message.edit(text)

    async def watcher(self, message):
        if not message or not message.sender_id or not message.chat:
            return
        
        chat_id = str(message.chat.id)
        if chat_id not in self.chat_settings or not self.chat_settings[chat_id]["enabled"]:
            return
        
        user_id = message.sender_id
        
        me = await self.client.get_me()
        if user_id == me.id:
            return
        
        try:
            sender = await message.get_sender()
            if sender and getattr(sender, 'bot', False):
                return
        except:
            pass
        
        if user_id in self.whitelist:
            return
        
        time_limit = self.chat_settings[chat_id]["time_limit"]
        current_time = time.time()
        last_time = self.cache.get(user_id, 0)
        
        if current_time - last_time < time_limit:
            await message.delete()
        
        self.cache[user_id] = current_time