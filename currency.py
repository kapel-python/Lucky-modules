# meta developer: @Lucky_modules

import asyncio
import aiohttp
from datetime import datetime
import xml.etree.ElementTree as ET
from .. import loader, utils
from telethon.tl.types import Message

@loader.tds
class CurrencyMod(loader.Module):
    """Модуль для получения курсов валют"""
    strings = {
        "name": "CurrencyRates",
        "error": "❌ Ошибка при получении данных: {}",
        "fetching": "⏳ Получаю курс валют...",
        "currency_menu": "💱 Выберите валюту:",
        "currency_view": "📊 Курс {currency}:\n\n{rates}\n\n⏰ Актуально на: {time}\n 🔗 Источник курсов: {source})",
    }
    currency_emojis = {
        "USD": "🇺🇸 USD",
        "EUR": "🇪🇺 EUR",
        "GBP": "🇬🇧 GBP",
        "CNY": "🇨🇳 CNY",
        "JPY": "🇯🇵 JPY",
        "BTC": "₿ BTC",
        "RUB": "🇷🇺 RUB",
    }

    async def client_ready(self, client, db):
        self.client = client

    async def crcmd(self, message: Message):
        """Получить курс валют"""
        await self._show_menu(message)

    async def _show_menu(self, message):
        c = list(self.currency_emojis.items())
        kb = [
            [{"text": c[i][1], "callback": self._on_select, "args": (c[i][0],)}] if i+1 == len(c)
            else [
                {"text": c[i][1], "callback": self._on_select, "args": (c[i][0],)},
                {"text": c[i+1][1], "callback": self._on_select, "args": (c[i+1][0],)},
            ]
            for i in range(0, len(c), 2)
        ]
        await self.inline.form(message=message, text=self.strings["currency_menu"], reply_markup=kb, silent=True)

    async def _on_select(self, call, cur):
        await call.edit(self.strings["fetching"])
        try:
            rates, src_rates = await self._fetch_rates()
            btc_usd, src_btc = await self._fetch_btc_usd()
            rates["btc_rub"] = rates["usd_rub"] * btc_usd
            source = f"{src_rates} и {src_btc}"
            txt = ""
            for code, name in self.currency_emojis.items():
                if code == cur: continue
                if cur == "RUB":
                    v = (1 / rates["btc_rub"] if code == "BTC" else 1 / rates[f"{code.lower()}_rub"])
                elif cur == "BTC":
                    v = (rates["btc_rub"] if code == "RUB" else rates["btc_rub"] / rates[f"{code.lower()}_rub"])
                elif code == "RUB":
                    v = rates[f"{cur.lower()}_rub"]
                elif code == "BTC":
                    v = rates[f"{cur.lower()}_rub"] / rates["btc_rub"]
                else:
                    v = rates[f"{cur.lower()}_rub"] / rates[f"{code.lower()}_rub"]
                txt += f"{name}: {self._fmt(v)}\n"
            resp = self.strings["currency_view"].format(
                currency=self.currency_emojis[cur],
                rates=txt.strip(),
                time=datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                source=source
            )
            kb = [
                [{"text": "🔄Обновить курс", "callback": self._on_select, "args": (cur,)}],
                [{"text": "🔙 Назад", "callback": self._on_back}]
            ]
            await call.edit(resp, reply_markup=kb)
        except Exception as e:
            await call.edit(self.strings["error"].format(e))

    async def _on_back(self, call):
        c = list(self.currency_emojis.items())
        kb = [
            [{"text": c[i][1], "callback": self._on_select, "args": (c[i][0],)}] if i+1 == len(c)
            else [
                {"text": c[i][1], "callback": self._on_select, "args": (c[i][0],)},
                {"text": c[i+1][1], "callback": self._on_select, "args": (c[i+1][0],)},
            ]
            for i in range(0, len(c), 2)
        ]
        await call.edit(self.strings["currency_menu"], reply_markup=kb)

    def _fmt(self, v):
        return f"{v:,.2f}".replace(",", " ") if v > 1000 else (
            f"{v:.8f}".rstrip("0").rstrip(".") if v < 0.001 else f"{v:.4f}".rstrip("0").rstrip(".")
        )

    async def _fetch_rates(self):
        async with aiohttp.ClientSession() as s:
            try:
                r = await s.get("https://www.cbr.ru/scripts/XML_daily.asp")
                xml = await r.text()
                tree = ET.fromstring(xml)
                m = {"USD": "usd_rub", "EUR": "eur_rub", "GBP": "gbp_rub", "CNY": "cny_rub", "JPY": "jpy_rub"}
                out = {v: float(tree.find(f".//Valute[CharCode='{k}']/Value").text.replace(",", ".")) /
                               int(tree.find(f".//Valute[CharCode='{k}']/Nominal").text)
                       for k, v in m.items()}
                return out, "CBR"
            except:
                r = await s.get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml")
                xml = await r.text()
                tree = ET.fromstring(xml)
                rates = {e.get("currency"): float(e.get("rate")) for e in tree.find(".//Cube").findall("Cube")}
                out = {
                    "usd_rub": 1 / rates["USD"],
                    "eur_rub": 1 / rates["EUR"],
                    "gbp_rub": 1 / rates.get("GBP", 1) and (1 / rates.get("GBP", 1)),
                    "cny_rub": None,
                    "jpy_rub": None
                }
                return out, "ECB"

    async def _fetch_btc_usd(self):
        async with aiohttp.ClientSession() as s:
            try:
                j = await (await s.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
                )).json()
                return j["bitcoin"]["usd"], "CoinGecko"
            except:
                j = await (await s.get(
                    "https://api.coindesk.com/v1/bpi/currentprice/USD.json"
                )).json()
                return float(j["bpi"]["USD"]["rate"].replace(",", "")), "Coindesk"
