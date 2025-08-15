# requires: google-generativeai
# meta developer: @Lucky_modules

import base64
import time
import json
import re
from .. import loader, utils
from google import genai

@loader.tds
class SmartTriggersMod(loader.Module):
    """Умные триггеры с ИИ анализом истории сообщений"""
    strings = {
        "name": "SmartTriggers",
        "cfg_api_key_doc": "API-ключ Gemini (https://aistudio.google.com/apikey?hl=ru)",
        "cfg_model_doc": "Модель Gemini (например: gemini-2.5-flash, gemini-2.5-pro)",
        "chat_enabled": "✅ Триггеры включены",
        "chat_disabled": "❌ Триггеры отключены",
        "chat_status": "🔄 {}",
        "need_reply": "❌ Ответь на сообщение для создания триггера. Например чтобы добавить триггер который на слово <b>привет</b> будет отвечать <b>Привет как дела</b>, то напиши сообщение <code>Привет как дела</code> и на него ответь командой <code>trigadd привет</code>",
        "trigger_added": "✅ Триггер <code>{}</code> добавлен (ID: <code>{}</code>)",
        "trigger_exists": "⚠️ Триггер <code>{}</code> уже есть",
        "trigger_deleted": "✅ Триггер с ID <code>{}</code> удалён",
        "trigger_not_found": "❌ Триггер с ID <code>{}</code> не найден",
        "mode_changed": "✅ Режим триггеров изменён на: {}",
        "trigger_list": "📋 Список триггеров ({}):\n\n{}\n\n🔒 - Строгий режим\n🔍 - Частичный режим\n🔐 - Приватный режим\n\nℹ️ Изменить режим триггера можно командой <code>.trig</code> id (<i>id это цифра перед названием триггера</i>)",
        "no_triggers": "ℹ️ В этом чате нет триггеров",
        "mode_menu": "🔧 Выбери режим работы триггеров:\n\n🔒 Строгий - Срабатывает только при точном совпадении фразы или слова\n\n🔍 Частичный - Срабатывает при наличии слова/фразы в тексте\n\n🔐 Приватный - Срабатывает только на твои сообщения\n\nℹ️ Смена режима работает только на новые триггеры, чтобы изменить режим уже созданных триггеров пиши <code>trig</code> ID триггера",
        "strict_mode": "Строгий",
        "partial_mode": "Частичный",
        "private_mode": "Приватный",
        "strict_desc": "Срабатывает только при точном совпадении фразы",
        "partial_desc": "Срабатывает при наличии фразы в тексте",
        "private_desc": "Срабатывает только на ваши собственные сообщения",
        "banned": "✅ Пользователь добавлен в чёрный список триггеров",
        "unbanned": "✅ Пользователь убран из чёрного списка триггеров",
        "already_banned": "⚠️ Пользователь уже в чёрном списке",
        "not_banned": "⚠️ Пользователя нет в чёрном списке",
        "ban_list": "📋 Чёрный список пользователей:\n\n{}",
        "empty_ban_list": "ℹ️ Чёрный список пользователей пуст",
        "trigger_info": "📍 Триггер #{}\n\n📝 Реагирует на слово/фразу: <code>{}</code>\n\n💬 Текст к триггеру: {}{}\n📊 Тип триггера: {}",
        "trigger_mode_changed": "✅ Режим триггера изменён на: {}",
        "change_trigger_mode": "Изменить тип триггера",
        "delete_trigger": "🗑️ Удалить триггер",
        "back_to_trigger": "↞ Назад",
        "invalid_trigger_id": "❌ Укажи ID триггера",
        "confirm_delete": "⚠️ Ты уверен что хочешь удалить этот триггер <code>{}</code>?\n\nПотом не вернешь обратно",
        "confirm_delete_yes": "✅ Конечно",
        "confirm_delete_no": "❌ Отмена",
        "spam_warning": "⚠️ Обнаружен спам триггерами\n{}, если продолжишь спам, ты будешь автоматически заблокирован для использования триггеров",
        "spam_banned": "🚫 {} заблокирован за спам триггерами",
        "ai_analyzing": "🤖 ИИ анализирует историю сообщений из чата...",
        "ai_no_api_key": "⚠️ Укажи API-ключ Gemini <code>.cfg SmartTriggers api_key</code>",
        "ai_analysis_result": "🤖 ИИ предлагает следующие триггеры:\n\n{}",
        "ai_no_suggestions": "🤖 ИИ не нашел подходящих триггеров в истории сообщений",
        "ai_error": "❌ Ошибка при обращении к ИИ:\n`{}`",
        "add_trigger_btn": "➕ Добавить триггер",
        "trigger_suggestion": "🔥 <b>Предложение триггера:</b>\n\n📝 Слово/фраза: <code>{}</code>\n💬 Ответ: <code>{}</code>\n\n❓ Хочешь добавить этот триггер?",
        "trigger_added_ai": "✅ Триггер добавлен из предложения ИИ!",
        "trigger_declined": "❌ Триггер отклонён",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", self.strings["cfg_api_key_doc"], validator=loader.validators.Hidden()),
            loader.ConfigValue("model", "gemini-2.5-flash", self.strings["cfg_model_doc"]),
        )
        self.db = None
        self.triggers = {}
        self.modes = {}
        self.spam_tracker = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.triggers = self.db.get("SmartTriggers", "triggers", {}) or {}
        self.modes = self.db.get("SmartTriggers", "modes", {}) or {}

    def check_spam(self, user_id, trigger_name):
        current_time = time.time()
        
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = {"triggers": [], "warned": False}
        
        user_data = self.spam_tracker[user_id]
        
        user_data["triggers"] = [
            (timestamp, trig_name) for timestamp, trig_name in user_data["triggers"] 
            if current_time - timestamp < 1.0
        ]
        
        user_data["triggers"].append((current_time, trigger_name))
        
        same_trigger_count = sum(1 for _, trig_name in user_data["triggers"] if trig_name == trigger_name)
        
        if same_trigger_count >= 3:
            if user_data["warned"]:
                return "ban"
            else:
                user_data["warned"] = True
                return "warn"
        
        return "continue"

    async def auto_ban_user(self, user_id):
        blacklist = self.db.get("SmartTriggers", "blacklist", []) or []
        if user_id not in blacklist:
            blacklist.append(user_id)
            self.db.set("SmartTriggers", "blacklist", blacklist)

    async def get_user_name(self, user_id):
        try:
            user = await self.client.get_entity(user_id)
            return user.first_name or "Пользователь"
        except:
            return "Пользователь"
            
    async def _resolve_user_id(self, message):
        if message.is_reply:
            reply_msg = await message.get_reply_message()
            return reply_msg.sender_id
        args = utils.get_args_raw(message)
        if not args:
            return None
        if args.isdigit():
            return int(args)
        username = args.lstrip('@')
        try:
            entity = await self.client.get_entity(username)
            return entity.id
        except:
            return None

    async def trigaicmd(self, message):
        """🤖 Анализ истории сообщений ИИ для предложения триггеров"""
        api_key = self.config["api_key"]
        model_name = self.config["model"]
        
        if not api_key:
            await utils.answer(message, self.strings["ai_no_api_key"])
            return

        await utils.answer(message, self.strings["ai_analyzing"])
        start_time = time.time()

        try:
            # Получаем последние 100 сообщений из чата
            messages = await self.client.get_messages(message.chat_id, limit=100)
            
            # Формируем текст истории для анализа
            history_text = ""
            for msg in reversed(messages):
                if msg.text and len(msg.text.strip()) > 0:
                    sender_name = "Пользователь"
                    try:
                        if msg.sender:
                            sender = await self.client.get_entity(msg.sender_id)
                            sender_name = sender.first_name or "Пользователь"
                    except:
                        pass
                    
                    history_text += f"{sender_name}: {msg.text}\n"

            if not history_text.strip():
                await utils.answer(message, "❌ В истории чата нет текстовых сообщений для анализа")
                return

            # Формируем промпт для ИИ
            prompt = (
                "Ты — эксперт по анализу чатов в Telegram. Проанализируй историю сообщений и предложи 3-5 популярных триггеров.\n"
                "Триггер — это слово или фраза, на которую бот будет отвечать определённым сообщением.\n\n"
                "Верни результат ТОЛЬКО в формате JSON без дополнительного текста:\n"
                '{"слово1": "ответ1", "слово2": "ответ2", "слово3": "ответ3"}\n\n'
                "Требования:\n"
                "- Анализируй только часто встречающиеся слова/фразы\n"
                "- Предлагай короткие, популярные триггеры\n"
                "- Ответы должны быть в стиле чата\n"
                "- Максимум 5 триггеров\n"
                "- Не используй мат и оскорбления\n\n"
                f"История сообщений:\n{history_text[:4000]}"  # Ограничиваем размер
            )

            # Отправляем запрос к Gemini
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            
            result = response.text.strip()
            
            # Парсим JSON ответ
            try:
                # Очищаем ответ от лишних символов
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = result[json_start:json_end]
                    suggestions = json.loads(json_str)
                else:
                    suggestions = json.loads(result)
                
                if not suggestions:
                    await utils.answer(message, self.strings["ai_no_suggestions"])
                    return
                
                # Показываем предложения с инлайн кнопками
                await self.show_ai_suggestions(message, suggestions)
                
            except json.JSONDecodeError as e:
                await utils.answer(message, f"❌ Ошибка парсинга ответа ИИ:\n`{e}`\n\nОтвет ИИ:\n{result}")
                
        except Exception as e:
            elapsed_time = round(time.time() - start_time, 2)
            await utils.answer(message, self.strings["ai_error"].format(str(e)))

    async def show_ai_suggestions(self, message, suggestions):
        """Показать предложения ИИ с инлайн кнопками"""
        suggestion_text = ""
        buttons = []
        
        for i, (trigger, response) in enumerate(suggestions.items(), 1):
            suggestion_text += f"{i}. <code>{trigger}</code> → <code>{response}</code>\n"
            buttons.append([{
                "text": f"➕ Добавить '{trigger}'",
                "callback": self.add_suggested_trigger,
                "args": (trigger, response, str(message.chat_id)),
            }])
        
        await self.inline.form(
            message=message,
            text=f"🤖 ИИ предлагает следующие триггеры:\n\n{suggestion_text}\n\n💡 Выбери какие триггеры добавить:",
            reply_markup=buttons,
            silent=True
        )

    async def add_suggested_trigger(self, call, trigger_name, response_text, chat_id):
        """Добавить предложенный ИИ триггер"""
        # Создаем временное сообщение с ответом для триггера
        temp_msg = await self.client.send_message(
            int(chat_id),
            response_text
        )
        
        # Добавляем триггер
        trigger_name = trigger_name.lower().strip()
        
        if chat_id not in self.triggers:
            self.triggers[chat_id] = {}
            
        if trigger_name in self.triggers[chat_id]:
            await call.answer("⚠️ Такой триггер уже существует!", show_alert=True)
            return
        
        trigger_id = len(self.triggers[chat_id]) + 1
        data = {
            "id": trigger_id,
            "mode": self.modes.get(str(call.from_user.id), "partial"),  # По умолчанию частичный режим для ИИ триггеров
            "chat_id": temp_msg.chat_id,
            "message_id": temp_msg.id
        }
        
        self.triggers[chat_id][trigger_name] = data
        self.db.set("SmartTriggers", "triggers", self.triggers)
        
        await call.answer(f"✅ Триггер '{trigger_name}' добавлен!", show_alert=False)
        
        # Обновляем сообщение
        updated_text = call.message.text + f"\n\n✅ Добавлен: <code>{trigger_name}</code>"
        await call.edit(updated_text, reply_markup=call.message.reply_markup)

    async def trigchatcmd(self, message):
        """Включить/выключить триггеры в текущем чате"""
        chat_id = str(message.chat_id)
        chats = self.db.get("SmartTriggers", "chats", {}) or {}
        new_status = not chats.get(chat_id, False)
        chats[chat_id] = new_status
        self.db.set("SmartTriggers", "chats", chats)
        status_text = self.strings["chat_enabled"] if new_status else self.strings["chat_disabled"]
        await utils.answer(message, self.strings["chat_status"].format(status_text))

    async def trigaddcmd(self, message):
        """Добавить триггер (в ответ на сообщение, которое будет являться ответом).Например чтобы добавить триггер который на слово 'привет' будет отвечать 'Привет как дела', то напиши сообщение 'Привет как дела' и на него ответь командой trigadd привет"""
        if not message.is_reply:
            await utils.answer(message, self.strings["need_reply"])
            return
        chat_id = str(message.chat_id)
        trigger_name = utils.get_args_raw(message).lower().strip()
        reply_msg = await message.get_reply_message()
        
        if chat_id not in self.triggers:
            self.triggers[chat_id] = {}
        if trigger_name in self.triggers[chat_id]:
            await utils.answer(message, self.strings["trigger_exists"].format(trigger_name))
            return
        
        trigger_id = len(self.triggers[chat_id]) + 1
        data = {
            "id": trigger_id, 
            "mode": self.modes.get(str(message.sender_id), "strict"),
            "chat_id": reply_msg.chat_id,
            "message_id": reply_msg.id
        }
        
        self.triggers[chat_id][trigger_name] = data
        self.db.set("SmartTriggers", "triggers", self.triggers)
        await utils.answer(message, self.strings["trigger_added"].format(trigger_name, trigger_id))

    async def trigcmd(self, message):
        """Показать информацию о триггере по ID.Пример: .trig 10"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, self.strings["invalid_trigger_id"])
            return
        
        trigger_id = int(args)
        chat_id = str(message.chat_id)
        
        if chat_id not in self.triggers or not self.triggers[chat_id]:
            await utils.answer(message, self.strings["no_triggers"])
            return
        
        trigger_data = None
        trigger_name = None
        for name, data in self.triggers[chat_id].items():
            if data["id"] == trigger_id:
                trigger_data = data
                trigger_name = name
                break
        
        if not trigger_data:
            await utils.answer(message, self.strings["trigger_not_found"].format(trigger_id))
            return
        
        try:
            msg = await self.client.get_messages(int(trigger_data["chat_id"]), ids=trigger_data["message_id"])
            text_content = msg.raw_text or "[без текста]"
            media_info = ""
            
            if msg.media:
                media_emoji = self.get_media_emoji(msg.media)
                media_type = self.get_media_type_name(msg.media)
                media_info = f"\n📋 Прикреплённый тип к триггеру: {media_type}\n\n"
        except:
            text_content = "[сообщение недоступно]"
            media_info = ""
        
        mode_name = {
            "strict": self.strings["strict_mode"],
            "partial": self.strings["partial_mode"], 
            "private": self.strings["private_mode"]
        }.get(trigger_data["mode"], trigger_data["mode"])
        
        info_text = self.strings["trigger_info"].format(
            trigger_id,
            trigger_name,
            text_content,
            media_info,
            mode_name
        )
        
        await self.inline.form(
            message=message,
            text=info_text,
            reply_markup=[
                [{
                    "text": self.strings["change_trigger_mode"],
                    "callback": self.show_trigger_mode_menu,
                    "args": (chat_id, trigger_name, trigger_id),
                }],
                [{
                    "text": self.strings["delete_trigger"],
                    "callback": self.confirm_trigger_delete,
                    "args": (chat_id, trigger_name, trigger_id),
                }]
            ],
            silent=True
        )

    async def confirm_trigger_delete(self, call, chat_id, trigger_name, trigger_id):
        confirm_text = self.strings["confirm_delete"].format(trigger_id, trigger_name)
        
        await call.edit(
            confirm_text,
            reply_markup=[
                [{
                    "text": self.strings["confirm_delete_yes"],
                    "callback": self.delete_trigger_confirmed,
                    "args": (chat_id, trigger_name, trigger_id),
                }],
                [{
                    "text": self.strings["confirm_delete_no"],
                    "callback": self.back_to_trigger_info,
                    "args": (chat_id, trigger_name, trigger_id),
                }]
            ]
        )

    async def delete_trigger_confirmed(self, call, chat_id, trigger_name, trigger_id):
        if chat_id in self.triggers and trigger_name in self.triggers[chat_id]:
            del self.triggers[chat_id][trigger_name]
            for idx, (_, data) in enumerate(self.triggers[chat_id].items(), 1):
                data["id"] = idx
                
            self.db.set("SmartTriggers", "triggers", self.triggers)
            
            await call.edit(
                self.strings["trigger_deleted"].format(trigger_id),
                reply_markup=[]
            )
        else:
            await call.edit(
                self.strings["trigger_not_found"].format(trigger_id),
                reply_markup=[]
            )

    async def show_trigger_mode_menu(self, call, chat_id, trigger_name, trigger_id):
        current_mode = self.triggers[chat_id][trigger_name]["mode"]

        def btn_text(mode_key):
            check = "✅ " if mode_key == current_mode else ""
            return f"{check}{self.strings[mode_key + '_mode']}"

        await call.edit(
            self.strings["mode_menu"],
            reply_markup=[
                [{
                    "text": btn_text("strict"),
                    "callback": self.set_trigger_mode,
                    "args": (chat_id, trigger_name, trigger_id, "strict"),
                }],
                [{
                    "text": btn_text("partial"),
                    "callback": self.set_trigger_mode,
                    "args": (chat_id, trigger_name, trigger_id, "partial"),
                }],
                [{
                    "text": btn_text("private"),
                    "callback": self.set_trigger_mode,
                    "args": (chat_id, trigger_name, trigger_id, "private"),
                }],
                [{
                    "text": self.strings["back_to_trigger"],
                    "callback": self.back_to_trigger_info,
                    "args": (chat_id, trigger_name, trigger_id),
                }]
            ]
        )

    async def set_trigger_mode(self, call, chat_id, trigger_name, trigger_id, new_mode):
        self.triggers[chat_id][trigger_name]["mode"] = new_mode
        self.db.set("SmartTriggers", "triggers", self.triggers)
        
        mode_name = {
            "strict": self.strings["strict_mode"],
            "partial": self.strings["partial_mode"], 
            "private": self.strings["private_mode"]
        }.get(new_mode, new_mode)
        
        await call.answer(self.strings["trigger_mode_changed"].format(mode_name), show_alert=False)
        await self.back_to_trigger_info(call, chat_id, trigger_name, trigger_id)

    async def back_to_trigger_info(self, call, chat_id, trigger_name, trigger_id):
        trigger_data = self.triggers[chat_id][trigger_name]
        
        try:
            msg = await self.client.get_messages(int(trigger_data["chat_id"]), ids=trigger_data["message_id"])
            text_content = msg.raw_text or "[без текста]"
            media_info = ""
            
            if msg.media:
                media_type = self.get_media_type_name(msg.media)
                media_info = f"\n📋 Прикреплённый тип к триггеру: {media_type}\n\n"
        except:
            text_content = "[сообщение недоступно]"
            media_info = ""
        
        mode_name = {
            "strict": self.strings["strict_mode"],
            "partial": self.strings["partial_mode"], 
            "private": self.strings["private_mode"]
        }.get(trigger_data["mode"], trigger_data["mode"])
        
        info_text = self.strings["trigger_info"].format(
            trigger_id,
            trigger_name,
            text_content,
            media_info,
            mode_name
        )
        
        await call.edit(
            info_text,
            reply_markup=[
                [{
                    "text": self.strings["change_trigger_mode"],
                    "callback": self.show_trigger_mode_menu,
                    "args": (chat_id, trigger_name, trigger_id),
                }],
                [{
                    "text": self.strings["delete_trigger"],
                    "callback": self.confirm_trigger_delete,
                    "args": (chat_id, trigger_name, trigger_id),
                }]
            ]
        )

    async def trigmodecmd(self, message):
        """Изменить режим работы триггеров"""
        user_id = str(message.sender_id)
        current_mode = self.modes.get(user_id, "strict")

        def btn_text(mode_key):
            check = "✅ " if mode_key == current_mode else ""
            return f"{check}{self.strings[mode_key + '_mode']}"

        await self.inline.form(
            message=message,
            text=self.strings["mode_menu"],
            reply_markup=[
                [{
                    "text": btn_text("strict"),
                    "callback": self.set_mode,
                    "args": ("strict",),
                    "description": self.strings["strict_desc"]
                }],
                [{
                    "text": btn_text("partial"),
                    "callback": self.set_mode,
                    "args": ("partial",),
                    "description": self.strings["partial_desc"]
                }],
                [{
                    "text": btn_text("private"),
                    "callback": self.set_mode,
                    "args": ("private",),
                    "description": self.strings["private_desc"]
                }]
            ],
            silent=True
        )

    async def set_mode(self, call, mode):
        user_id = str(call.from_user.id)
        self.modes[user_id] = mode
        self.db.set("SmartTriggers", "modes", self.modes)

        def btn_text(mode_key):
            check = "✅ " if mode_key == mode else ""
            return f"{check}{self.strings[mode_key + '_mode']}"

        await call.edit(
            self.strings["mode_menu"],
            reply_markup=[
                [{
                    "text": btn_text("strict"),
                    "callback": self.set_mode,
                    "args": ("strict",),
                    "description": self.strings["strict_desc"]
                }],
                [{
                    "text": btn_text("partial"),
                    "callback": self.set_mode,
                    "args": ("partial",),
                    "description": self.strings["partial_desc"]
                }],
                [{
                    "text": btn_text("private"),
                    "callback": self.set_mode,
                    "args": ("private",),
                    "description": self.strings["private_desc"]
                }]
            ]
        )
        mode_name = {
            "strict": self.strings["strict_mode"],
            "partial": self.strings["partial_mode"], 
            "private": self.strings["private_mode"]
        }.get(mode, mode)
        
        await call.answer(self.strings["mode_changed"].format(mode_name), show_alert=False)

    async def trigdelcmd(self, message):
        """Удалить триггер по ID"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, "❌ Укажи ID триггера для удаления (ID находтится в triglist)")
            return
        trigger_id = int(args)
        chat_id = str(message.chat_id)
        if chat_id not in self.triggers or not self.triggers[chat_id]:
            await utils.answer(message, self.strings["no_triggers"])
            return
        deleted = False
        for trigger_name, data in list(self.triggers[chat_id].items()):
            if data["id"] == trigger_id:
                del self.triggers[chat_id][trigger_name]
                deleted = True
                break
        if deleted:
            for idx, (_, data) in enumerate(self.triggers[chat_id].items(), 1):
                data["id"] = idx
            self.db.set("SmartTriggers", "triggers", self.triggers)
            await utils.answer(message, self.strings["trigger_deleted"].format(trigger_id))
        else:
            await utils.answer(message, self.strings["trigger_not_found"].format(trigger_id))

    def get_media_emoji(self, media):
        if not media:
            return ""
        
        if hasattr(media, 'photo'):
            return "[📷]"
        elif hasattr(media, 'document'):
            if hasattr(media.document, 'mime_type'):
                mime = media.document.mime_type
                if mime == 'application/x-tgsticker':
                    return "[🎪]"
                elif mime.startswith('video/'):
                    return "[🎬]"
                elif mime.startswith('audio/'):
                    return "[🎵]"
                elif mime.startswith('image/'):
                    return "[🖼️]"
                else:
                    return "[📋]"
            if hasattr(media.document, 'attributes'):
                for attr in media.document.attributes:
                    attr_type = type(attr).__name__
                    if 'DocumentAttributeSticker' in attr_type:
                        return "[🎪]"
                    elif 'DocumentAttributeVideo' in attr_type:
                        if hasattr(attr, 'round_message') and attr.round_message:
                            return "[⭕]" 
                        else:
                            return "[🎬]"
                    elif 'DocumentAttributeAudio' in attr_type:
                        if hasattr(attr, 'voice') and attr.voice:
                            return "[🎙]"
                        else:
                            return "[🎵]" 
            return "[📋]"
        else:
            return "[📋]"

    def get_media_type_name(self, media):
        if not media:
            return "Неизвестный тип"
        
        if hasattr(media, 'photo'):
            return "Фото"
        elif hasattr(media, 'document'):
            if hasattr(media.document, 'mime_type'):
                mime = media.document.mime_type
                if mime == 'application/x-tgsticker':
                    return "Стикер"
                elif mime.startswith('video/'):
                    return "Видеофайл"
                elif mime.startswith('audio/'):
                    return "Аудиофайл"
                elif mime.startswith('image/'):
                    return "Изображение"
                elif mime.startswith('text/'):
                    return "Текстовый файл"
                else:
                    return "Документ"
            if hasattr(media.document, 'attributes'):
                for attr in media.document.attributes:
                    attr_type = type(attr).__name__
                    if 'DocumentAttributeSticker' in attr_type:
                        return "Стикер"
                    elif 'DocumentAttributeVideo' in attr_type:
                        if hasattr(attr, 'round_message') and attr.round_message:
                            return "Видео сообщение"
                        else:
                            return "Видео"
                    elif 'DocumentAttributeAudio' in attr_type:
                        if hasattr(attr, 'voice') and attr.voice:
                            return "Голосовое сообщение"
                        else:
                            return "Аудио"
            return "Документ"
        else:
            return "Медиафайл"

    async def triglistcmd(self, message):
        """Показать список всех триггеров"""
        chat_id = str(message.chat_id)
        if chat_id not in self.triggers or not self.triggers[chat_id]:
            await utils.answer(message, self.strings["no_triggers"])
            return
        triggers = self.triggers[chat_id]
        count = len(triggers)
        trigger_list = []
        for trigger_name, data in triggers.items():
            mode_emoji = {
                "strict": "🔒",
                "partial": "🔍", 
                "private": "🔐"
            }.get(data["mode"], "🔒")
            
            preview = ""
            try:
                msg = await self.client.get_messages(int(data["chat_id"]), ids=data["message_id"])
                if msg.media:
                    preview += self.get_media_emoji(msg.media)
                    if msg.raw_text:
                        text_preview = msg.raw_text[:30]
                        if len(msg.raw_text) > 30:
                            text_preview += "..."
                        preview += f" {text_preview}"
                else:
                    if msg.raw_text:
                        text_preview = msg.raw_text[:30]
                        if len(msg.raw_text) > 30:
                            text_preview += "..."
                        preview = text_preview
            except:
                preview = "[сообщение недоступно]"
            
            trigger_list.append(
                f"<code>{data['id']}</code>. {mode_emoji} <code>{trigger_name}</code> → {preview}"
            )
        await utils.answer(message, self.strings["trigger_list"].format(count, "\n".join(trigger_list)))

    async def trigbancmd(self, message):
        """Заблокировать пользователя (ID / @username / реплай)"""
        user_id = await self._resolve_user_id(message)
        if not user_id:
            await utils.answer(message, "❌ Укажи ID/юзернейм или ответь на сообщение")
            return
        blacklist = self.db.get("SmartTriggers", "blacklist", []) or []
        if user_id in blacklist:
            await utils.answer(message, self.strings["already_banned"])
            return
        blacklist.append(user_id)
        self.db.set("SmartTriggers", "blacklist", blacklist)
        await utils.answer(message, self.strings["banned"])

    async def trigunbancmd(self, message):
        """Разблокировать пользователя (ID / @username / реплай)"""
        user_id = await self._resolve_user_id(message)
        if not user_id:
            await utils.answer(message, "❌ Укажи ID/юзернейм или ответь на сообщение")
            return
        blacklist = self.db.get("SmartTriggers", "blacklist", []) or []
        if user_id not in blacklist:
            await utils.answer(message, self.strings["not_banned"])
            return
        blacklist.remove(user_id)
        self.db.set("SmartTriggers", "blacklist", blacklist)
        await utils.answer(message, self.strings["unbanned"])

    async def trigbanlistcmd(self, message):
        """Показать чёрный список"""
        blacklist = self.db.get("SmartTriggers", "blacklist", []) or []
        if not blacklist:
            await utils.answer(message, self.strings["empty_ban_list"])
            return
        
        ban_list = []
        for user_id in blacklist:
            try:
                user = await self.client.get_entity(user_id)
                name = user.first_name or "Без имени"
                
                if hasattr(user, 'username') and user.username:
                    user_link = f'<a href="https://t.me/{user.username}">{name}</a>'
                else:
                    user_link = f'<a href="tg://user?id={user_id}">{name}</a>'
                
                ban_list.append(f"{user_link}")
            except:
                user_link = f'<a href="tg://user?id={user_id}">Удалённый аккаунт</a>'
                ban_list.append(f"{user_link} (ID <code>{user_id}</code>)")
        
        await utils.answer(message, self.strings["ban_list"].format("\n".join(ban_list)))

    async def watcher(self, message):
        if not message.text:
            return
        chat_id = str(message.chat_id)
        chats = self.db.get("SmartTriggers", "chats", {}) or {}
        if not chats.get(chat_id, False):
            return
        if chat_id not in self.triggers or not self.triggers[chat_id]:
            return
        blacklist = self.db.get("SmartTriggers", "blacklist", []) or []
        if message.sender_id in blacklist:
            return
        
        text = message.text.lower()
        for trigger_name, data in self.triggers[chat_id].items():
            match = False
            
            if data["mode"] == "private":
                if not message.out:
                    continue
                    
                if text.strip() == trigger_name.strip():
                    match = True
            elif data["mode"] == "strict":
                if text.strip() == trigger_name.strip():
                    match = True
            else:
                if trigger_name in text:
                    match = True
                    
            if match:
                spam_check = self.check_spam(message.sender_id, trigger_name)
                
                if spam_check == "warn":
                    user_name = await self.get_user_name(message.sender_id)
                    warning_text = self.strings["spam_warning"].format(user_name)
                    await self.client.send_message(
                        message.chat_id,
                        warning_text,
                        reply_to=message.id
                    )
                    return
                elif spam_check == "ban":
                    await self.auto_ban_user(message.sender_id)
                    user_name = await self.get_user_name(message.sender_id)
                    ban_text = self.strings["spam_banned"].format(user_name)
                    await self.client.send_message(
                        message.chat_id,
                        ban_text,
                        reply_to=message.id
                    )
                    return
                
                try:
                    original_msg = await self.client.get_messages(int(data["chat_id"]), ids=data["message_id"])
                    if original_msg.media and hasattr(original_msg.media, "document") or hasattr(original_msg.media, "photo"):
                        await self.client.send_message(
                            message.chat_id,
                            original_msg.message or "",
                            reply_to=message.id,
                            file=original_msg.media
                        )
                    else:
                        await self.client.send_message(
                            message.chat_id,
                            original_msg.message or "",
                            reply_to=message.id
                        )
                    
                except Exception as e:
                    error_info = f"❌ Ошибка триггера '{trigger_name}':\n"
                    error_info += f"Сохранённый chat_id: {data.get('chat_id', 'НЕ НАЙДЕН')}\n"
                    error_info += f"Сохранённый message_id: {data.get('message_id', 'НЕ НАЙДЕН')}\n"
                    error_info += f"Ошибка: {str(e)}"
                    await self.client.send_message(
                        message.chat_id,
                        error_info,
                        reply_to=message.id
                    )