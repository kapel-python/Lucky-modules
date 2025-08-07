# meta developer: @Lucky_modules
import asyncio
import math
import re
from multiprocessing import Process, Queue
from .. import loader, utils
from telethon.tl.types import Message

@loader.tds
class CalcMod(loader.Module):
    """Калькулятор с расширенными настройками и интерактивным меню 🧮"""

    strings = {"name": "Calculator"}

    def __init__(self):
        self.settings = {
            "max_time": 5.0,          
            "round_digits": 10,        
            "show_formula": True,      
            "percent_handling": True, 
            "error_detail": "brief"    
        }

    async def client_ready(self, client, db):
        self.db = db
        saved_settings = self.db.get("calc", "settings", {})
        self.settings.update(saved_settings)
        self.db.set("calc", "settings", self.settings)

    async def calccmd(self, message):
        """Вычислить математическое выражение. Формат: .calc <выражение>"""
        expr = utils.get_args_raw(message)
        if not expr:
            await utils.answer(message, "🔴 Ошибка: Вы не указали выражение")
            return

        
        original_expr = expr

        
        expr = (
            expr.replace("^", "**")
            .replace("π", "pi")
            .replace("×", "*")
            .replace("÷", "/")
            .replace(",", ".")
        )

        expr = re.sub(r"√\s*(\d+\.?\d*)", r"sqrt(\1)", expr, flags=re.IGNORECASE)
        expr = re.sub(r"√\s*\((.+?)\)", r"sqrt(\1)", expr, flags=re.IGNORECASE)
        
        if self.settings["percent_handling"]:
            expr = self._parse_percents(expr)

        
        allowed_names = {
            "pi": math.pi,
            "e": math.e,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "radians": math.radians,
            "degrees": math.degrees,
            "sum": sum,
            "range": range,
            "abs": abs,
            "round": round,
            "factorial": math.factorial
        }

        queue = Queue()
        process = Process(target=self._eval_worker, args=(expr, queue, allowed_names))
        process.start()
        process.join(timeout=self.settings["max_time"])

        if process.is_alive():
            process.terminate()
            buttons = [
                [{"text": "⚙️ Изменить время выполнения", "callback": self.calc_time_callback}],
                [{"text": "📊 Открыть настройки", "callback": self.calcsettings_callback}]
            ]
            await self.inline.form(
                message=message,
                text=f"⏳ Выражение {original_expr} выполнялось дольше {self.settings['max_time']} сек!",
                reply_markup=buttons,
                ttl=10 * 60
            )
            return

        result = queue.get()
        if isinstance(result, Exception):
            if self.settings["error_detail"] == "full":
                error_text = (
                    f"🔴 Ошибка вычисления:\n"
                    f"Тип: {type(result).__name__}\n"
                    f"Сообщение: {str(result)}\n"
                    f"Выражение: <code>{original_expr}</code>"
                )
            else:
                error_text = f"🔴 Ошибка вычисления: {str(result)}"
            
            await utils.answer(message, error_text)
            return

        
        if isinstance(result, float):
            result = round(result, self.settings["round_digits"])
            if result.is_integer():
                result = int(result)

        if self.settings["show_formula"]:
            response = (
                f"🧮 Выражение: <code>{original_expr}</code>\n"
                f"✨ Результат: <code>{result}</code>"
            )
        else:
            response = f"✨ Результат: <code>{result}</code>"

        await utils.answer(message, response)

    async def calcsetcmd(self, message):
        """Открыть настройки калькулятора"""
        await self.calcsettings_callback(message)

    async def calcsettings_callback(self, event):
        """Обработчик открытия настроек"""
        text = (
            "⚙️ <b>Настройки калькулятора</b>\n\n"
            f"• ⏳ Время выполнения: <code>{self.settings['max_time']}</code> сек\n"
            f"• 🔢 Точность округления: <code>{self.settings['round_digits']}</code> знаков\n"
            f"• 📝 Показывать выражение: {'✅' if self.settings['show_formula'] else '❌'}\n"
            f"• 📊 Обработка процентов: {'✅' if self.settings['percent_handling'] else '❌'}\n"
            f"• 🚨 Детализация ошибок: {'Подробная' if self.settings['error_detail'] == 'full' else 'Краткая'}"
        )

        buttons = [
            [{"text": "⏳ Время выполнения", "callback": self.calc_time_callback}],
            [{"text": "🔢 Точность округления", "callback": self.calc_round_callback}],
            [{"text": f"📝 Показ выражения {'✅' if self.settings['show_formula'] else '❌'}", 
              "callback": self.toggle_formula_callback}],
            [{"text": f"📊 Проценты: {'✅' if self.settings['percent_handling'] else '❌'}", 
              "callback": self.toggle_percent_callback}],
            [{"text": f"🚨 Ошибки: {'Подробные' if self.settings['error_detail'] == 'full' else 'Краткие'}", 
              "callback": self.toggle_error_detail_callback}]
        ]

        
        if isinstance(event, Message):
            await self.inline.form(
                message=event,
                text=text,
                reply_markup=buttons,
                ttl=10 * 60
            )
        else:
            await event.edit(
                text=text,
                reply_markup=buttons
            )

    async def calc_time_callback(self, call):
        """Обработчик кнопки времени выполнения"""
        text = (
            "⏳ <b>Настройки времени выполнения</b>\n\n"
            "ℹ️ Максимальное время выполнения выражения, после истечения которого выполнение завершится\n\n"
            f"Текущее значение: <code>{self.settings['max_time']}</code> сек\n"
            "Выберите новое значение:"
        )

        buttons = [
            [{"text": "⚡️ 1 сек", "callback": self.set_time_callback, "args": (1.0,)}],
            [{"text": "🚀 3 сек", "callback": self.set_time_callback, "args": (3.0,)}],
            [{"text": "🐢 5 сек", "callback": self.set_time_callback, "args": (5.0,)}],
            [{"text": "🐌 10 сек", "callback": self.set_time_callback, "args": (10.0,)}],
            [{"text": "🔙 Назад", "callback": self.calcsettings_callback}]
        ]

        await call.edit(
            text=text,
            reply_markup=buttons
        )

    async def calc_round_callback(self, call):
        """Обработчик кнопки точности округления"""
        text = (
            "🔢 <b>Настройки точности округления</b>\n\n"
            "ℹ️ Количество знаков после запятой для округления результата\n\n"
            f"Текущее значение: <code>{self.settings['round_digits']}</code> знаков\n"
            "Выберите новое значение:"
        )

        buttons = [
            [{"text": "0 знаков", "callback": self.set_round_callback, "args": (0,)}],
            [{"text": "2 знака", "callback": self.set_round_callback, "args": (2,)}],
            [{"text": "4 знака", "callback": self.set_round_callback, "args": (4,)}],
            [{"text": "6 знаков", "callback": self.set_round_callback, "args": (6,)}],
            [{"text": "10 знаков", "callback": self.set_round_callback, "args": (10,)}],
            [{"text": "🔙 Назад", "callback": self.calcsettings_callback}]
        ]

        await call.edit(
            text=text,
            reply_markup=buttons
        )

    async def set_time_callback(self, call, new_time):
        """Установка нового времени выполнения"""
        self.settings["max_time"] = new_time
        self.db.set("calc", "settings", self.settings)
        await call.answer(f"✅ Время выполнения установлено: {new_time} сек", show_alert=True)
        await self.calcsettings_callback(call)

    async def set_round_callback(self, call, new_round):
        """Установка новой точности округления"""
        self.settings["round_digits"] = new_round
        self.db.set("calc", "settings", self.settings)
        await call.answer(f"✅ Точность округления установлена: {new_round} знаков", show_alert=True)
        await self.calcsettings_callback(call)

    async def toggle_formula_callback(self, call):
        """Переключение показа формулы"""
        self.settings["show_formula"] = not self.settings["show_formula"]
        self.db.set("calc", "settings", self.settings)
        status = "включен" if self.settings["show_formula"] else "выключен"
        await self.calcsettings_callback(call)

    async def toggle_percent_callback(self, call):
        """Переключение обработки процентов"""
        self.settings["percent_handling"] = not self.settings["percent_handling"]
        self.db.set("calc", "settings", self.settings)
        status = "включена" if self.settings["percent_handling"] else "выключена"
        await self.calcsettings_callback(call)

    async def toggle_error_detail_callback(self, call):
        """Переключение детализации ошибок"""
        self.settings["error_detail"] = "full" if self.settings["error_detail"] == "brief" else "brief"
        self.db.set("calc", "settings", self.settings)
        status = "подробные" if self.settings["error_detail"] == "full" else "краткие"
        await self.calcsettings_callback(call)

    def _parse_percents(self, expr: str) -> str:
        """Умная обработка процентов"""
        # Обработка специальных случаев: X + Y%
        expr = re.sub(
            r'(\d+\.?\d*)\s*([\+\-])\s*(\d+\.?\d*)\s*%', 
            lambda m: f"{m.group(1)} {m.group(2)} ({m.group(1)} * {m.group(3)} / 100)", 
            expr
        )
        
        
        expr = re.sub(
            r'(\d+\.?\d*)\s*([\*\/])\s*(\d+\.?\d*)\s*%', 
            lambda m: f"{m.group(1)} {m.group(2)} ({m.group(3)} / 100)", 
            expr
        )
        
        expr = re.sub(
            r'(\d+\.?\d*)\s*%', 
            r'(\1 / 100)', 
            expr
        )
        
        return expr

    def _eval_worker(self, expr: str, queue: Queue, allowed_names: dict):
        """Выполнение вычислений в отдельном процессе"""
        try:
            result = eval(
                expr,
                {"__builtins__": {}},
                allowed_names
            )
            queue.put(result)
        except Exception as e:
            queue.put(e)
