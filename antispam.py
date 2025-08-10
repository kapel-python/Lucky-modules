# meta developer: @Lucky_modules

__version__ = (1, 1, 4)

from .. import loader, utils
import time

class AntiSpamModule(loader.Module):
    """Модуль для защиты от спама в чатах"""
    strings = {"name": "AntiSpam"}

    def __init__(self):
        self.cache = {}
        self.chat_settings = {}

    async def client_ready(self, client, db):
        self.db = db
        self.chat_settings = self.db.get("antispam", "chat_settings", {})

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

    async def watcher(self, message):
        if not message or not message.sender_id or not message.chat:
            return
        
        chat_id = str(message.chat.id)
        if chat_id not in self.chat_settings or not self.chat_settings[chat_id]["enabled"]:
            return
        
        user_id = message.sender_id
        time_limit = self.chat_settings[chat_id]["time_limit"]
        current_time = time.time()
        last_time = self.cache.get(user_id, 0)
        
        if current_time - last_time < time_limit:
            await message.delete()
            self.cache[user_id] = current_time
            return
        
        self.cache[user_id] = current_time
