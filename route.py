# meta developer: @Lucky_modules
import asyncio
from .. import loader, utils
from telethon.tl.types import Message
import requests


API_KEY = "49aeb6ba-6f16-4af9-bf08-3de61d38beea"


@loader.tds
class RouteMod(loader.Module):
    """Построение маршрута на общественном транспорте через 2GIS"""

    strings = {"name": "Route"}

    def __init__(self):
        self.config_name = "Route"

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if not self.db.get(self.config_name, "states"):
            self.db.set(self.config_name, "states", {})

    # --------------------- STATE UTILS ---------------------
    def _get_states(self):
        return self.db.get(self.config_name, "states", {})

    def _save_states(self, states):
        self.db.set(self.config_name, "states", states)

    def _state_key(self, chat_id, user_id):
        return f"{chat_id}:{user_id}"

    def _get_state(self, chat_id, user_id):
        return self._get_states().get(self._state_key(chat_id, user_id), {})

    def _set_state(self, chat_id, user_id, state):
        states = self._get_states()
        states[self._state_key(chat_id, user_id)] = state
        self._save_states(states)

    def _clear_state(self, chat_id, user_id):
        states = self._get_states()
        states.pop(self._state_key(chat_id, user_id), None)
        self._save_states(states)

    # --------------------- API CALLS ---------------------
    async def geocode_address(self, address):
        def _req():
            url = "https://catalog.api.2gis.com/3.0/items/geocode"
            params = {
                "q": address,
                "fields": "items.point,items.full_name,items.name",
                "key": API_KEY,
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    items = (data.get("result") or {}).get("items") or []
                    if items:
                        first = items[0]
                        point = first.get("point") or {}
                        display_name = first.get("full_name") or first.get("name") or address
                        if "lat" in point and "lon" in point:
                            return {
                                "lat": point["lat"],
                                "lon": point["lon"],
                                "name": display_name,
                            }
                return None
            except Exception:
                return None

        return await asyncio.to_thread(_req)

    async def get_public_transport_route(self, source, target):
        def _req():
            url = "https://routing.api.2gis.com/public_transport/2.0"
            params = {"key": API_KEY}
            body = {
                "source": {"name": source["name"], "point": {"lat": source["lat"], "lon": source["lon"]}},
                "target": {"name": target["name"], "point": {"lat": target["lat"], "lon": target["lon"]}},
                "transport": [
                    "bus",
                    "trolleybus",
                    "tram",
                    "metro",
                    "suburban_train",
                ],
                "locale": "ru",
                "max_result_count": 5,
                "enable_schedule": True,
            }
            try:
                resp = requests.post(url, params=params, json=body, headers={"Content-Type": "application/json"}, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                return None
            except Exception:
                return None

        return await asyncio.to_thread(_req)

    # --------------------- FORMATTERS ---------------------
    def _format_duration(self, seconds):
        seconds = int(seconds or 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours} ч {minutes} мин"
        return f"{minutes} мин"

    def _format_routes_text(self, routes):
        if not routes:
            return "❌ Не удалось получить маршрут"

        lines = []
        lines.append("📊 Найдено вариантов маршрута: <b>{}</b>".format(len(routes)))
        max_show = min(3, len(routes))
        for idx in range(max_show):
            route = routes[idx]
            total_dur = self._format_duration(route.get("total_duration", 0))
            transfers = route.get("transfer_count", 0)
            lines.append("")
            lines.append(f"<b>🚌 ВАРИАНТ #{idx+1}</b>")
            lines.append(f"🕐 Общее время: <b>{total_dur}</b>")
            lines.append(f"🔁 Пересадок: <b>{transfers}</b>")

            movements = route.get("movements", []) or []
            if movements:
                lines.append("📋 Детали:")
                for i, movement in enumerate(movements, 1):
                    move_type = movement.get("type", "")
                    waypoint = movement.get("waypoint", {}) or {}
                    comment = waypoint.get("comment", "")
                    if move_type == "walkway":
                        if comment:
                            lines.append(f"  {i}. 🚶 {comment}")
                        else:
                            lines.append(f"  {i}. 🚶 Пешеходный переход")
                    elif move_type == "passage":
                        parts = []
                        metro = movement.get("metro", {}) or {}
                        routes_part = movement.get("routes", []) or []
                        platforms = movement.get("platforms", {}) or {}
                        final_stop = None
                        names = platforms.get("names") or []
                        if names:
                            final_stop = names[-1]

                        if metro:
                            line_name = metro.get("line_name") or ""
                            direction = metro.get("ui_direction_suggest") or ""
                            station_count = metro.get("ui_station_count") or ""
                            metro_str = "🚇 Метро"
                            if line_name:
                                metro_str += f" ({line_name})"
                            if direction:
                                metro_str += f" в сторону {direction}"
                            if station_count:
                                metro_str += f" ({station_count})"
                            parts.append(metro_str)

                        for r in routes_part:
                            subtype = r.get("subtype") or ""
                            names = r.get("names") or []
                            if names:
                                route_numbers = ", ".join(names)
                                if subtype == "bus":
                                    parts.append(f"🚌 Автобус {route_numbers}")
                                elif subtype == "trolleybus":
                                    parts.append(f"🚎 Троллейбус {route_numbers}")
                                elif subtype == "tram":
                                    parts.append(f"🚊 Трамвай {route_numbers}")
                                elif subtype == "suburban_train":
                                    parts.append(f"🚆 Электричка {route_numbers}")
                                else:
                                    parts.append(f"🚋 {route_numbers}")

                        if parts:
                            lines.append(f"  {i}. {' → '.join(parts)}")
                            if final_stop:
                                lines.append(f"     🎯 Ехать до: {final_stop}")

                        moving_duration = movement.get("moving_duration")
                        if moving_duration:
                            lines.append(f"     ⏱️ Время в пути: {self._format_duration(moving_duration)}")

        return "\n".join(lines)

    # --------------------- COMMAND FLOW ---------------------
    async def routecmd(self, message: Message):
        """Построить маршрут (интерактивно)"""
        user_id = message.sender_id
        chat_id = message.chat_id

        await message.delete()
        prompt = await utils.answer(message, "📍 Введите начальную точку")
        self._set_state(chat_id, user_id, {
            "phase": "await_from",
            "prompt_id": prompt.id,
        })

    async def watcher(self, message):
        if not message or not message.text or not message.sender_id or not message.chat:
            return

        chat_id = message.chat_id
        user_id = message.sender_id
        state = self._get_state(chat_id, user_id)
        if not state:
            return

        phase = state.get("phase")
        if phase == "await_from":
            from_text = message.raw_text.strip()
            await message.delete()
            prompt = await utils.answer(message, "🎯 Введите конечную точку")
            state.update({
                "phase": "await_to",
                "from_text": from_text,
                "prompt_id": prompt.id,
            })
            self._set_state(chat_id, user_id, state)
            return

        if phase == "await_to":
            to_text = message.raw_text.strip()
            await message.delete()

            from_geocoded = await self.geocode_address(state.get("from_text", ""))
            to_geocoded = await self.geocode_address(to_text)

            if not from_geocoded:
                self._clear_state(chat_id, user_id)
                await utils.answer(message, "❌ Ошибка геокодирования начальной точки. Попробуйте снова: .route")
                return

            if not to_geocoded:
                self._clear_state(chat_id, user_id)
                await utils.answer(message, "❌ Ошибка геокодирования конечной точки. Попробуйте снова: .route")
                return

            confirm_text = (
                "Проверьте данные:\n\n"
                f"📍 Начало: <b>{from_geocoded['name']}</b>\n"
                f"🎯 Конец: <b>{to_geocoded['name']}</b>"
            )

            buttons = [
                [{"text": "🧭 Проложить маршрут", "callback": self._confirm_route}],
                [{"text": "❌ Отменить", "callback": self._cancel_route}],
            ]

            self._set_state(chat_id, user_id, {
                "phase": "confirm",
                "from": from_geocoded,
                "to": to_geocoded,
            })

            await self.inline.form(
                message=message,
                text=confirm_text,
                reply_markup=buttons,
                silent=True,
            )
            return

    # --------------------- CALLBACKS ---------------------
    async def _cancel_route(self, call):
        chat_id = call.form.chat_id if hasattr(call, "form") else call.message.chat_id
        user_id = call.from_user.id if hasattr(call, "from_user") else call.sender_id
        self._clear_state(chat_id, user_id)
        await call.edit("🚫 Отменено")

    async def _confirm_route(self, call):
        chat_id = call.form.chat_id if hasattr(call, "form") else call.message.chat_id
        user_id = call.from_user.id if hasattr(call, "from_user") else call.sender_id
        state = self._get_state(chat_id, user_id)
        source = state.get("from")
        target = state.get("to")
        if not source or not target:
            await call.answer("Данные не найдены. Запустите снова: .route", show_alert=True)
            self._clear_state(chat_id, user_id)
            return

        await call.edit("⏳ Строю маршрут...")
        data = await self.get_public_transport_route(source, target)

        routes = []
        if data:
            routes = ((data.get("result") or {}).get("routes") or [])
            routes = sorted(routes, key=lambda r: r.get("total_duration", 0))

        text = self._format_routes_text(routes)
        await call.edit(text)
        self._clear_state(chat_id, user_id)

