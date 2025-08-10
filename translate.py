# meta developer: @Lucky_modules
# requires: deep_translator

import asyncio
from .. import loader, utils
from telethon.tl.types import Message
from deep_translator import GoogleTranslator
import functools
import logging

logger = logging.getLogger(__name__)

@loader.tds
class TranslateMod(loader.Module):
    """Переводчик с выбором сервиса перевода"""
    strings = {"name": "Translate"}

    def __init__(self):
        self.config_name = "Translate"

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if not self.db.get(self.config_name, "settings"):
            self.db.set(self.config_name, "settings", {
                "from": "auto",
                "to": "ru",
                "service": "deep_translate"
            })

    def get_default_settings(self):
        return {
            "from": "auto",
            "to": "ru",
            "service": "deep_translate"
        }

    def get_settings(self):
        settings = self.db.get(self.config_name, "settings")
        if not settings:
            settings = self.get_default_settings()
            self.db.set(self.config_name, "settings", settings)
        
        default = self.get_default_settings()
        for key, value in default.items():
            if key not in settings:
                settings[key] = value
        
        return settings

    async def translatecmd(self, message: Message):
        """Перевести текст [text/reply]"""
        text = utils.get_args_raw(message)
        is_reply = False
        
        if not text and message.is_reply:
            msg = await message.get_reply_message()
            text = msg.raw_text
            is_reply = True
            
        if not text:
            await utils.answer(message, "❌ Напиши после команды текст или ответь на сообщение командой")
            return

        processing = await utils.answer(message, "🔄 Перевожу...")
        settings = self.get_settings()
        
        try:
            translated = await self.translate_text(text, settings["from"], settings["to"], settings["service"])
        except Exception as e:
            logger.exception("Translation error")
            await utils.answer(processing, f"❌ Ошибка перевода: {str(e)}")
            return

        
        if is_reply:
            result = f"🌐 Перевод:\n\n<blockquote><code>{translated}</blockquote></code>"
        else:
            result = (
                f"💬 Исходный текст:\n<blockquote><code>{text}</blockquote></code>\n\n"
                f"🌐 Перевод:\n<blockquote><code>{translated}</blockquote></code>"
            )

        await utils.answer(processing, result)

    async def translatesetcmd(self, message: Message):
        """Настройки переводчика"""
        await self.show_settings_menu(message)

    async def show_settings_menu(self, event):
        settings = self.get_settings()
        buttons = [
            [{"text": "🔠 Исходный язык: " + self.lang_label(settings["from"]), "callback": self.set_from}],
            [{"text": "🔤 Язык перевода: " + self.lang_label(settings["to"]), "callback": self.set_to}],
            [{"text": "🛠 Сервис перевода: " + self.service_label(settings["service"]), "callback": self.set_service}],
        ]
        
        if isinstance(event, Message):
            await self.inline.form(
                message=event,
                text="🛠 Настройки перевода",
                reply_markup=buttons,
                silent=True
            )
        else:
            await event.edit(
                text="🛠 Настройки перевода",
                reply_markup=buttons
            )

    async def set_from(self, call):
        await self.lang_select(call, "from")

    async def set_to(self, call):
        await self.lang_select(call, "to")

    async def set_service(self, call):
        settings = self.get_settings()
        selected = settings["service"]
        buttons = [
            [{"text": ("✅ " if selected == "deep_translate" else "") + "Deep Translate", "callback": self.select_service, "args": ("deep_translate",)}],
            [{"text": ("✅ " if selected == "translatepy" else "") + "TranslatePy", "callback": self.select_service, "args": ("translatepy",)}],
            [{"text": "↩️ Назад", "callback": self.show_settings_menu}]
        ]
        await call.edit("🛠 Выбери сервис перевода:\n\n💬 Описание: Выбор сервиса для выполнения перевода текста. Deep Translate - стабильный сервис\nTranslatePy - альтернативный многосервисный переводчик", reply_markup=buttons)

    async def select_service(self, call, service):
        settings = self.get_settings()
        settings["service"] = service
        self.db.set(self.config_name, "settings", settings)
        await self.set_service(call)
        await call.answer(f"✅ Сервис изменен: {self.service_label(service)}")

    async def lang_select(self, call, key):
        settings = self.get_settings()
        selected = settings[key]
        langs = [
            ("🇷🇺 Русский", "ru"),
            ("🇬🇧 English", "en"),
            ("🇨🇳 中文 (упрощенный)", "zh-CN"),
            ("🇹🇼 中文 (традиционный)", "zh-TW"),
            ("🇯🇵 日本語", "ja"),
            ("🇸🇦 العربية", "ar"),
            ("🇪🇸 Español", "es"),
            ("🇫🇷 Français", "fr"),
            ("🇩🇪 Deutsch", "de"),
            ("🇮🇹 Italiano", "it"),
            ("🇵🇱 Polski", "pl"),
            ("🇺🇦 Українська", "uk"),
            ("🇰🇷 한국어", "ko"),
            ("🇵🇹 Português", "pt"),
            ("🇹🇷 Türkçe", "tr"),
            ("🇳🇱 Nederlands", "nl"),
            ("🇮🇳 हिन्दी", "hi"),
            ("🇹🇭 ไทย", "th"),
]
        
        if key == "from":
            langs.insert(0, ("🌐 Автоматически", "auto"))
            
        buttons = [
            [{"text": ("✅ " if selected == code else "") + label, "callback": self.select_lang, "args": (key, code)}]
            for label, code in langs
        ]
        buttons.append([{"text": "↩️ Назад", "callback": self.show_settings_menu}])
        
        description = "💬 Описание: Выбор исходного языка для перевода. Выбери <b>Автоматически</b> для автоматического определения языка" if key == "from" else "💬 Описание: Выбор языка, на который будет переведен текст"
        
        await call.edit(f"🌐 Выбери язык:\n\n{description}", reply_markup=buttons)

    async def select_lang(self, call, key, value):
        settings = self.get_settings()
        settings[key] = value
        self.db.set(self.config_name, "settings", settings)
        await self.lang_select(call, key)
        await call.answer(f"✅ Язык изменен: {self.lang_label(value)}")

    async def translate_text(self, text, lang_from, lang_to, service):
        if lang_from == "auto":
            lang_from = 'auto'
        
        loop = asyncio.get_event_loop()
        
        if service == "deep_translate":
            def sync_translate():
                translator = GoogleTranslator(source=lang_from, target=lang_to)
                return translator.translate(text)
        else:
            def sync_translate():
                try:
                    from translatepy import Translator
                    translator = Translator()
                    result = translator.translate(text, source_language=lang_from, destination_language=lang_to)
                    return result.result
                except ImportError:
                    translator = GoogleTranslator(source=lang_from, target=lang_to)
                    return translator.translate(text)
                except Exception:
                    translator = GoogleTranslator(source=lang_from, target=lang_to)
                    return translator.translate(text)
        
        return await loop.run_in_executor(None, sync_translate)

    def lang_label(self, code):
        labels = {
            "auto": "Автоматически",
            "ru": "Русский",
            "en": "English",
            "zh-CN": "中文 (упрощенный)",
            "zh-TW": "中文 (традиционный)",
            "ja": "日本語",
            "ar": "العربية",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pl": "Polski",
            "uk": "Українська",
            "ko": "한국어",
            "pt": "Português",
            "tr": "Türkçe",
            "nl": "Nederlands",
            "hi": "हिन्दी",
            "th": "ไทย",
        }
        return labels.get(code, code)

    def service_label(self, service):
        labels = {
            "deep_translate": "Deep Translate",
            "translatepy": "TranslatePy"
        }
        return labels.get(service, service)
