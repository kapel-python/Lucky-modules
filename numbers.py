# meta developer: @Lucky_modules

from .. import loader, utils
import asyncio

@loader.tds
class NumberPrinterMod(loader.Module):
    """Печатает числа от и до"""
    strings = {"name": "NumberPrinter"}

    def __init__(self):
        self.running = {}

    async def client_ready(self, client, db):
        self.set("delay", self.get("delay", 1.0))

    async def numspeedcmd(self, message):
        """Устанавливает задержку между числами или показывает текущую"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, f"⚙️ Текущая задержка: {self.get('delay', 1.0)} сек.")
            return
        try:
            delay = float(args[0])
            if delay <= 0:
                raise ValueError
            self.set("delay", delay)
            await utils.answer(message, f"✅ Задержка установлена: {delay} сек.")
        except ValueError:
            await utils.answer(message, "❌ Введи положительное число. Пример: .numspeed 0.5")

    async def numbercmd(self, message):
        """Печатает числа с задержкой"""
        args = utils.get_args(message)
        if len(args) != 2:
            await utils.answer(message, "❌ Формат: .number 1 10")
            return

        try:
            start, end = map(int, args)
        except ValueError:
            await utils.answer(message, "❌ Аргументы должны быть целыми числами")
            return

        delay = self.get("delay", 1.0)
        chat_id = message.chat_id
        self.running[chat_id] = True

        await message.delete()

        step = 1 if start <= end else -1
        for i in range(start, end + step, step):
            if not self.running.get(chat_id):
                break
            try:
                await message.client.send_message(chat_id, str(i))
                await asyncio.sleep(delay)
            except Exception as e:
                await message.client.send_message(chat_id, f"❌ Ошибка отправки: {e}")
                break

        self.running.pop(chat_id, None)

    async def stopcmd(self, message):
        """Останавить"""
        chat_id = message.chat_id
        self.running[chat_id] = False
        await message.delete()

    async def numinfocmd(self, message):
        """Инфо"""
        chat_id = message.chat_id
        delay = self.get("delay", 1.0)
        active = "Да" if self.running.get(chat_id) else "Нет"
        await utils.answer(message, f"ℹ️ Задержка: <code>{delay}</code> сек.\n⏳ Активный вывод: <b>{active}</b>")
