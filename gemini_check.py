# requires: google-generativeai
# meta developer: @Lucky_modules
# requires: google-genai google

import base64
import time
from .. import loader, utils
from google import genai

@loader.tds
class GeminiCheckMod(loader.Module):
    """Проверка модулей через Gemini"""
    strings = {
        "name": "GeminiCheck",
        "cfg_api_key_doc": "API-ключ Gemini (https://aistudio.google.com/apikey?hl=ru)",
        "cfg_model_doc": "Модель Gemini (например: gemini-2.5-flash, gemini-2.5-pro)"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", self.strings["cfg_api_key_doc"], validator=loader.validators.Hidden()),
            loader.ConfigValue("model", "gemini-2.5-flash", self.strings["cfg_model_doc"]),
        )

    async def gemcheckcmd(self, message):
        """Проверить модуль [в ответ на файл]"""
        reply = await message.get_reply_message()
        if not reply or not reply.file or not reply.file.name.endswith(".py"):
            return await message.edit("⚠️ Ответь на .py файл")

        api_key = self.config["api_key"]
        model_name = self.config["model"]
        if not api_key:
            return await message.edit("⚠️ Укажи API-ключ Gemini <code>.cfg Geminicheck api_key</code>")

        await message.edit("🔎 Проверка модуля...")
        start_time = time.time()

        file_bytes = await reply.download_media(bytes)
        code_text = file_bytes.decode(errors="ignore")
        line_count = len(code_text.splitlines())

        prompt = (
            "Ты — эксперт по безопасности Python-кода для Telegram-юзерботов.\n"
            "Дай сверхкраткий отчёт в формате:\n"
            "🔴 Критические угрозы: (1 короткая фраза или 'нет'). К этим угрозам относятся кража данных, удаление аккаунта, несанкционированный доступ к аккаунту и другое.\n"
            "🟠 Предупреждения: (1 короткая фраза или 'нет')\n"
            "🔵 Информация: (1 короткая фраза, что делает код)\n"
            "Не используй сложных предложений и лишние детали.\n\n"
            f"Код модуля:\n```python\n{code_text}\n```"
        )

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    {"role": "user", "parts": [{"text": prompt}]},
                    {"role": "user", "parts": [{"inline_data": {"mime_type": "text/x-python", "data": base64.b64encode(file_bytes).decode()}}]},
                ],
            )
            result = response.text.strip()
        except Exception as e:
            result = f"❌ Ошибка при запросе к Gemini:\n`{e}`"

        elapsed_time = round(time.time() - start_time, 2)
        result += f"\n\n⏱ Время проверки: {elapsed_time:.0f} сек\n📏 Строк кода: {line_count}\n🧠 Модель: {model_name} (можно изменить командой <code>.cfg Geminicheck model</code>"


        await message.edit(result if result else "⚠️ Gemini не вернул ответа")
      
