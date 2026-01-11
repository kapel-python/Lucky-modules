
__version__ = (1, 1, 0)

# meta developer: @Lucky_modules

from .. import loader, utils
from telethon.tl.functions.payments import GetStarsStatusRequest, GetStarsTransactionsRequest
from telethon.tl.types import InputPeerSelf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@loader.tds
class StarsAnalyzerMod(loader.Module):
    """Модуль для просмотра баланса и транзакций твоих звездачек"""
    
    strings = {
        "name": "StarsAnalyzer",
        "loading": "<emoji document_id=5451646226975955576>⌛</emoji> Загружаю данные Stars...",
        "error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {}",
        "no_data": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось получить данные Stars",
        "main_stats": """<emoji document_id=5188311512791393083>🌟</emoji> <b>Telegram Stars</b>

<emoji document_id=5818865088970362886>💰</emoji> <b>Баланс:</b>
├ Текущий: <code>{balance:,} ⭐</code>
└ Всего получено: <code>{total_earned:,} ⭐</code>

<emoji document_id=5188377234380954537>📊</emoji> <b>Транзакции:</b>
├ Всего: <code>{total_count}</code>
├ Получено: <code>{incoming_count}</code> (+{incoming_sum:,} ⭐)
└ Потрачено: <code>{outgoing_count}</code> (-{outgoing_sum:,} ⭐)

<emoji document_id=5188186017847682895>⏰</emoji> <b>Обновлено:</b> <code>{timestamp}</code>""",
        
        "stats_with_transactions": """<emoji document_id=5188311512791393083>🌟</emoji> <b>Telegram Stars</b>

<emoji document_id=5818865088970362886>💰</emoji> <b>Баланс:</b>
├ Текущий: <code>{balance:,} ⭐</code>
└ Всего получено: <code>{total_earned:,} ⭐</code>

<emoji document_id=5188377234380954537>📊</emoji> <b>Транзакции:</b>
├ Всего: <code>{total_count}</code>
├ Получено: <code>{incoming_count}</code> (+{incoming_sum:,} ⭐)
└ Потрачено: <code>{outgoing_count}</code> (-{outgoing_sum:,} ⭐)

<emoji document_id=5188208041783826635>📋</emoji> <b>Последние {shown_count} транзакций:</b>
{recent_transactions}

<emoji document_id=5188182847026354347>🔝</emoji> <b>Топ-3 транзакции:</b>
{top_transactions}

<emoji document_id=5188186017847682895>⏰</emoji> <b>Обновлено:</b> <code>{timestamp}</code>""",
        
        "no_transactions": "└ Нет транзакций",
        "balance_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка получения баланса",
        "transactions_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка получения транзакций",
        "show_transactions": "📋 Показать транзакции",
        "hide_transactions": "🔼 Скрыть транзакции",
        "refresh": "🔄 Обновить",
        "_cfg_transactions_count": "Количество транзакций для отображения",
        "_cfg_show_transaction_id": "Показывать ID транзакции",
        "_cfg_show_peer_details": "Показывать детали получателя/отправителя",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "transactions_count",
                5,
                lambda: self.strings["_cfg_transactions_count"],
                validator=loader.validators.Integer(minimum=1)
            ),
            loader.ConfigValue(
                "show_transaction_id",
                False,
                lambda: self.strings["_cfg_show_transaction_id"],
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "show_peer_details",
                True,
                lambda: self.strings["_cfg_show_peer_details"],
                validator=loader.validators.Boolean()
            ),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def _get_stars_balance(self):
        try:
            result = await self.client(GetStarsStatusRequest(peer=InputPeerSelf()))
            
            if hasattr(result, 'balance'):
                if hasattr(result.balance, 'amount'):
                    return result.balance.amount
                return result.balance
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting stars balance: {e}")
            return None

    async def _get_stars_transactions(self, limit=50):
        try:
            result = await self.client(GetStarsTransactionsRequest(
                peer=InputPeerSelf(),
                offset="",
                limit=limit
            ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting stars transactions: {e}")
            return None

    def _parse_transaction(self, tx):
        try:
            
            stars = 0
            if hasattr(tx, 'amount'):
                amount_obj = tx.amount
                if hasattr(amount_obj, 'amount'):
                    stars = amount_obj.amount
                elif isinstance(amount_obj, (int, float)):
                    stars = int(amount_obj)
            
            description = "Транзакция"
            tx_type = "unknown"
            additional_info = []
            if hasattr(tx, 'gift') and tx.gift:
                description = "Подарок"
                tx_type = "gift"
                if hasattr(tx.gift, 'stars'):
                    additional_info.append(f"Звезд в подарке: {tx.gift.stars}")
            
            elif hasattr(tx, 'stargift') and tx.stargift:
                description = "Телеграм Gift"
                tx_type = "stargift"
                if hasattr(tx, 'stargift_upgrade') and tx.stargift_upgrade:
                    description = "Телеграм Gift (улучшенный)"
                    additional_info.append("Тип: Улучшение")
                elif hasattr(tx, 'stargift_resale') and tx.stargift_resale:
                    description = "Телеграм Gift (перепроданный)"
                    additional_info.append("Тип: Перепродажа")
            
            elif hasattr(tx, 'reaction') and tx.reaction:
                description = "Реакция"
                tx_type = "reaction"
                if hasattr(tx, 'msg_id'):
                    additional_info.append(f"Сообщение: {tx.msg_id}")
            
            elif hasattr(tx, 'subscription_period') and tx.subscription_period:
                description = "Подписка"
                tx_type = "subscription"
                additional_info.append(f"Период: {tx.subscription_period}")
            
            elif hasattr(tx, 'giveaway_post_id') and tx.giveaway_post_id:
                description = "Розыгрыш"
                tx_type = "giveaway"
                additional_info.append(f"Post ID: {tx.giveaway_post_id}")
            
            elif hasattr(tx, 'title') and tx.title:
                description = str(tx.title)
                tx_type = "titled"
            
            elif hasattr(tx, 'description') and tx.description:
                description = str(tx.description)
                tx_type = "described"
            
            elif hasattr(tx, 'extended_media') and tx.extended_media:
                description = "Платный контент"
                tx_type = "media"
                additional_info.append("Медиа контент")
            
            elif hasattr(tx, 'paid_messages') and tx.paid_messages:
                description = "Платные сообщения"
                tx_type = "paid_messages"
            
            if hasattr(tx, 'starref_amount') and tx.starref_amount:
                additional_info.append(f"Реферал: {tx.starref_amount} ⭐")
            
            if hasattr(tx, 'starref_commission_permille') and tx.starref_commission_permille:
                commission_percent = tx.starref_commission_permille / 10
                additional_info.append(f"Комиссия: {commission_percent}%")
            
            if hasattr(tx, 'premium_gift_months') and tx.premium_gift_months:
                additional_info.append(f"Premium: {tx.premium_gift_months} мес.")
            
            date = 0
            if hasattr(tx, 'date') and tx.date:
                if hasattr(tx.date, 'timestamp'):
                    date = int(tx.date.timestamp())
                else:
                    date = int(tx.date)
            
            peer_info = "Telegram"
            peer_id = None
            
            if hasattr(tx, 'peer') and tx.peer:
                peer_wrapper = tx.peer
                peer_type_wrapper = type(peer_wrapper).__name__
                
                if 'Fragment' in peer_type_wrapper:
                    peer_info = '<a href="https://fragment.com/stars">Fragment</a>'
                elif 'AppStore' in peer_type_wrapper:
                    peer_info = "App Store"
                elif 'PlayMarket' in peer_type_wrapper:
                    peer_info = "Play Market"
                elif 'PremiumBot' in peer_type_wrapper:
                    peer_info = "Premium Bot"
                elif 'Ads' in peer_type_wrapper:
                    peer_info = "Telegram Ads"
                elif hasattr(peer_wrapper, 'peer'):
                    
                    inner_peer = peer_wrapper.peer
                    inner_peer_type = type(inner_peer).__name__
                    
                    if 'User' in inner_peer_type and hasattr(inner_peer, 'user_id'):
                        peer_id = inner_peer.user_id
                       
                        peer_info = f"USER_PLACEHOLDER_{peer_id}"
                    elif 'Channel' in inner_peer_type and hasattr(inner_peer, 'channel_id'):
                        peer_id = inner_peer.channel_id
                        
                        peer_info = f"CHANNEL_PLACEHOLDER_{peer_id}"
                    elif 'Chat' in inner_peer_type and hasattr(inner_peer, 'chat_id'):
                        peer_id = inner_peer.chat_id
                        peer_info = f'<a href="tg://openmessage?chat_id={peer_id}">Chat {peer_id}</a>'
                    else:
                        peer_info = inner_peer_type.replace('Peer', '')
                else:
                    peer_info = peer_type_wrapper.replace('StarsTransactionPeer', '')
            
            if hasattr(tx, 'starref_peer') and tx.starref_peer:
                ref_peer = tx.starref_peer
                if hasattr(ref_peer, 'user_id'):
                    additional_info.append(f"Реферал User: {ref_peer.user_id}")
            
            transaction_id = None
            if hasattr(tx, 'id') and tx.id:
                transaction_id = str(tx.id)
            
            transaction_url = None
            if hasattr(tx, 'transaction_url') and tx.transaction_url:
                transaction_url = tx.transaction_url
            
            status_flags = []
            
            if hasattr(tx, 'refund') and tx.refund:
                status_flags.append("refund")
                description = f"Возврат: {description}"
            
            if hasattr(tx, 'pending') and tx.pending:
                status_flags.append("pending")
                description = f"⏳ {description}"
            
            if hasattr(tx, 'failed') and tx.failed:
                status_flags.append("failed")
                description = f"❌ {description}"
            
            return {
                'amount': stars,
                'description': description,
                'date': date,
                'peer': peer_info,
                'peer_id': peer_id,
                'is_outgoing': stars < 0,
                'type': tx_type,
                'transaction_id': transaction_id,
                'transaction_url': transaction_url,
                'additional_info': additional_info,
                'status_flags': status_flags
            }
            
        except Exception as e:
            logger.exception(f"Error parsing transaction: {e}")
            return None

    def _analyze_transactions(self, transactions_result):
        stats = {
            'total_count': 0,
            'incoming_count': 0,
            'outgoing_count': 0,
            'incoming_sum': 0,
            'outgoing_sum': 0,
            'transactions': []
        }
        
        if not transactions_result:
            return stats
        
        try:
            tx_list = []
            
            if hasattr(transactions_result, 'history'):
                for tx in transactions_result.history:
                    parsed = self._parse_transaction(tx)
                    if parsed:
                        tx_list.append(parsed)
            
            stats['transactions'] = tx_list
            stats['total_count'] = len(tx_list)
            
            for tx in tx_list:
                amount = tx['amount']
                
                if amount > 0:
                    stats['incoming_count'] += 1
                    stats['incoming_sum'] += amount
                elif amount < 0:
                    stats['outgoing_count'] += 1
                    stats['outgoing_sum'] += abs(amount)
            
        except Exception as e:
            logger.error(f"Error analyzing transactions: {e}")
        
        return stats

    async def _resolve_peer_info(self, peer_info):
        try:
            if peer_info.startswith("USER_PLACEHOLDER_"):
                user_id = int(peer_info.replace("USER_PLACEHOLDER_", ""))
                try:
                    user = await self.client.get_entity(user_id)
                    if hasattr(user, 'username') and user.username:
                        return f'<a href="https://t.me/{user.username}">@{user.username}</a>'
                    elif hasattr(user, 'first_name'):
                        name = user.first_name
                        if hasattr(user, 'last_name') and user.last_name:
                            name += f" {user.last_name}"
                        return f'<a href="tg://openmessage?user_id={user_id}">{name}</a>'
                    else:
                        return f'<a href="tg://openmessage?user_id={user_id}">User {user_id}</a>'
                except Exception as e:
                    logger.error(f"Error resolving user {user_id}: {e}")
                    return f'<a href="tg://openmessage?user_id={user_id}">User {user_id}</a>'
            
            elif peer_info.startswith("CHANNEL_PLACEHOLDER_"):
                channel_id = int(peer_info.replace("CHANNEL_PLACEHOLDER_", ""))
                try:
                    channel = await self.client.get_entity(channel_id)
                    if hasattr(channel, 'username') and channel.username:
                        return f'<a href="https://t.me/{channel.username}">@{channel.username}</a>'
                    elif hasattr(channel, 'title'):
                        return f'<a href="tg://resolve?domain={channel_id}">{channel.title}</a>'
                    else:
                        return f'<a href="tg://resolve?domain={channel_id}">Channel {channel_id}</a>'
                except Exception as e:
                    logger.error(f"Error resolving channel {channel_id}: {e}")
                    return f'<a href="tg://resolve?domain={channel_id}">Channel {channel_id}</a>'
            return peer_info
            
        except Exception as e:
            logger.error(f"Error resolving peer info: {e}")
            return peer_info

    async def _resolve_all_peers(self, transactions):
        for tx in transactions:
            if tx.get('peer'):
                tx['peer'] = await self._resolve_peer_info(tx['peer'])
        return transactions

    def _format_transaction(self, tx, separator="├"):
        try:
            if tx['amount'] > 0:
                emoji = "💰"
                tx_type = "Получено"
            else:
                emoji = "💸"
                tx_type = "Потрачено"
            
            desc = tx['description'][:30]
            if len(tx['description']) > 30:
                desc += "..."
            
            date_str = "N/A"
            if tx['date'] > 0:
                dt = datetime.fromtimestamp(tx['date'])
                date_str = dt.strftime("%d.%m %H:%M")
            
            result = f"{separator} {emoji} {tx_type} | <code>{abs(tx['amount']):,} ⭐</code>\n"
            result += f"│  ├ {date_str} | {desc}\n"
            
            if self.config["show_peer_details"] and tx.get('peer'):
                result += f"│  ├ 👤 {tx['peer']}\n"
            
            if tx.get('additional_info'):
                for info in tx['additional_info']:
                    result += f"│  ├ ℹ️ {info}\n"
            
            if self.config["show_transaction_id"] and tx.get('transaction_id'):
                tx_id_short = tx['transaction_id'][:20] + "..." if len(tx['transaction_id']) > 20 else tx['transaction_id']
                result += f"│  ├ 🔑 ID: <code>{tx_id_short}</code>\n"
            result = result.rstrip('\n')
            last_line_start = result.rfind('\n│  ├')
            if last_line_start != -1:
                result = result[:last_line_start] + '\n│  └' + result[last_line_start+5:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {e}")
            return f"{separator} ⚠️ Ошибка форматирования"

    @loader.command()
    async def stars(self, message):
        """Информация о твоих звездочках"""
        
        msg = await utils.answer(message, self.strings["loading"])
        
        try:
            balance = await self._get_stars_balance()
            
            if balance is None:
                await utils.answer(msg, self.strings["balance_error"])
                return
            
            transactions_result = await self._get_stars_transactions(limit=50)
            
            stats = self._analyze_transactions(transactions_result)
            
            if stats['transactions']:
                stats['transactions'] = await self._resolve_all_peers(stats['transactions'])
            
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            result = self.strings["main_stats"].format(
                balance=balance,
                total_earned=stats['incoming_sum'],
                total_count=stats['total_count'],
                incoming_count=stats['incoming_count'],
                incoming_sum=stats['incoming_sum'],
                outgoing_count=stats['outgoing_count'],
                outgoing_sum=stats['outgoing_sum'],
                timestamp=timestamp
            )
            
            buttons = [
                [
                    {
                        "text": self.strings["show_transactions"],
                        "callback": self._show_transactions_callback,
                        "args": (balance, stats, timestamp)
                    }
                ],
                [
                    {
                        "text": self.strings["refresh"],
                        "callback": self._refresh_callback
                    }
                ]
            ]
            
            await self.inline.form(
                text=result,
                message=msg,
                reply_markup=buttons
            )
            
        except Exception as e:
            logger.exception("Error in stars command")
            await utils.answer(msg, self.strings["error"].format(str(e)))

    async def _show_transactions_callback(self, call, balance, stats, timestamp):
        try:
            transactions_count = self.config["transactions_count"]
            
            recent_tx_text = ""
            if stats['transactions']:
                shown_transactions = stats['transactions'][:transactions_count]
                for i, tx in enumerate(shown_transactions):
                    separator = "└" if i == len(shown_transactions) - 1 else "├"
                    recent_tx_text += self._format_transaction(tx, separator) + "\n"
            else:
                recent_tx_text = self.strings["no_transactions"]
            
            top_tx_text = ""
            if stats['transactions']:
                sorted_tx = sorted(
                    stats['transactions'],
                    key=lambda x: abs(x['amount']),
                    reverse=True
                )[:3]
                
                for i, tx in enumerate(sorted_tx):
                    separator = "└" if i == len(sorted_tx) - 1 else "├"
                    top_tx_text += self._format_transaction(tx, separator) + "\n"
            else:
                top_tx_text = self.strings["no_transactions"]
            result = self.strings["stats_with_transactions"].format(
                balance=balance,
                total_earned=stats['incoming_sum'],
                total_count=stats['total_count'],
                incoming_count=stats['incoming_count'],
                incoming_sum=stats['incoming_sum'],
                outgoing_count=stats['outgoing_count'],
                outgoing_sum=stats['outgoing_sum'],
                shown_count=min(transactions_count, len(stats['transactions'])),
                recent_transactions=recent_tx_text.rstrip(),
                top_transactions=top_tx_text.rstrip(),
                timestamp=timestamp
            )
            
            buttons = [
                [
                    {
                        "text": self.strings["hide_transactions"],
                        "callback": self._hide_transactions_callback,
                        "args": (balance, stats, timestamp)
                    }
                ],
                [
                    {
                        "text": self.strings["refresh"],
                        "callback": self._refresh_callback
                    }
                ]
            ]
            
            await call.edit(
                text=result,
                reply_markup=buttons
            )
            
        except Exception as e:
            logger.exception("Error showing transactions")
            await call.answer(f"Ошибка: {str(e)}", show_alert=True)

    async def _hide_transactions_callback(self, call, balance, stats, timestamp):
        try:
            result = self.strings["main_stats"].format(
                balance=balance,
                total_earned=stats['incoming_sum'],
                total_count=stats['total_count'],
                incoming_count=stats['incoming_count'],
                incoming_sum=stats['incoming_sum'],
                outgoing_count=stats['outgoing_count'],
                outgoing_sum=stats['outgoing_sum'],
                timestamp=timestamp
            )
            
            buttons = [
                [
                    {
                        "text": self.strings["show_transactions"],
                        "callback": self._show_transactions_callback,
                        "args": (balance, stats, timestamp)
                    }
                ],
                [
                    {
                        "text": self.strings["refresh"],
                        "callback": self._refresh_callback
                    }
                ]
            ]
            
            await call.edit(
                text=result,
                reply_markup=buttons
            )
            
        except Exception as e:
            logger.exception("Error hiding transactions")
            await call.answer(f"Ошибка: {str(e)}", show_alert=True)

    async def _refresh_callback(self, call):
        try:
            await call.answer("🔄 Обновление...")
            
            balance = await self._get_stars_balance()
            
            if balance is None:
                await call.answer(self.strings["balance_error"], show_alert=True)
                return
            
            transactions_result = await self._get_stars_transactions(limit=50)
            stats = self._analyze_transactions(transactions_result)
            
            if stats['transactions']:
                stats['transactions'] = await self._resolve_all_peers(stats['transactions'])
            
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            result = self.strings["main_stats"].format(
                balance=balance,
                total_earned=stats['incoming_sum'],
                total_count=stats['total_count'],
                incoming_count=stats['incoming_count'],
                incoming_sum=stats['incoming_sum'],
                outgoing_count=stats['outgoing_count'],
                outgoing_sum=stats['outgoing_sum'],
                timestamp=timestamp
            )
            
            buttons = [
                [
                    {
                        "text": self.strings["show_transactions"],
                        "callback": self._show_transactions_callback,
                        "args": (balance, stats, timestamp)
                    }
                ],
                [
                    {
                        "text": self.strings["refresh"],
                        "callback": self._refresh_callback
                    }
                ]
            ]
            
            await call.edit(
                text=result,
                reply_markup=buttons
            )
            
            await call.answer("✅ Обновлено!")
            
        except Exception as e:
            logger.exception("Error refreshing")
            await call.answer(f"Ошибка: {str(e)}", show_alert=True)

    @loader.command()
    async def starsdebug(self, message):
        """Команда для разработчиков. Я задолбался искать правильный подход к api stars поэтому вот вам готовенькое, напримеи если захочешь добавить что то свое"""
        
        msg = await utils.answer(message, "🔍 Получаю данные...")
        
        try:
            transactions_result = await self._get_stars_transactions(limit=5)
            
            if not transactions_result:
                await utils.answer(msg, "❌ Нет данных")
                return
            
            debug_info = f"<b>Отладочная информация:</b>\n\n"
            
            if hasattr(transactions_result, 'history'):
                debug_info += f"<b>Транзакций в истории:</b> {len(transactions_result.history)}\n\n"
                
                for i, tx in enumerate(transactions_result.history[:3]):
                    debug_info += f"<b>Транзакция {i+1}:</b>\n"
                    debug_info += f"├ Тип: {type(tx).__name__}\n"
                    
                    if hasattr(tx, 'amount'):
                        debug_info += f"├ Amount: {tx.amount}\n"
                    
                    if hasattr(tx, 'date'):
                        debug_info += f"├ Date: {tx.date}\n"
                    
                    if hasattr(tx, 'peer'):
                        debug_info += f"├ Peer присутствует: {tx.peer is not None}\n"
                        if tx.peer:
                            debug_info += f"├ Peer тип: {type(tx.peer).__name__}\n"
                            debug_info += f"├ Peer атрибуты: {', '.join([a for a in dir(tx.peer) if not a.startswith('_')])}\n"
                            debug_info += f"├ Peer строка: {str(tx.peer)[:100]}\n"
                            
                            if hasattr(tx.peer, 'user_id'):
                                debug_info += f"├ Peer user_id: {tx.peer.user_id}\n"
                            if hasattr(tx.peer, 'channel_id'):
                                debug_info += f"├ Peer channel_id: {tx.peer.channel_id}\n"
                            if hasattr(tx.peer, 'chat_id'):
                                debug_info += f"├ Peer chat_id: {tx.peer.chat_id}\n"
                        else:
                            debug_info += f"├ Peer is None\n"
                    else:
                        debug_info += f"├ Peer не найден\n"
                    
                    debug_info += f"└───\n\n"
            
            await utils.answer(msg, debug_info)
            
        except Exception as e:
            logger.exception("Error in starsdebug")
            await utils.answer(msg, f"❌ Ошибка: {str(e)}")