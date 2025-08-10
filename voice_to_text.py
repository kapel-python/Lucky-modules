# meta developer: @Lucky_modules
# requires: SpeechRecognition
import os
import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from .. import loader, utils
import math

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

@loader.tds
class VoiceToTextMod(loader.Module):
    """Модуль для рачшифровки ГС"""
    strings = {
        "name": "VoiceToText",
        "processing": "🔊 Распознаю ГС...",
        "no_voice": "❌ Это не голосовое сообщение",
        "download_error": "❌ Ошибка загрузки аудио",
        "convert_error": "❌ Ошибка конвертации аудио",
        "recognition_error": "❌ Ошибка распознавания: {}",
        "result": "🔊 Я распознал:\n\n<blockquote>{}</blockquote>",
        "timeout_error": "⏰ Я распознавал больше 1 минуты (это слишком долго). Вот что я успел распознать:\n\n<blockquote>{}</blockquote>",
        "chat_enabled": "✅ Автораспознавание голоса включено в этом чате",
        "chat_disabled": "❌ Автораспознавание голоса отключено в этом чате",
        "chat_status": "🔄 Автораспознавание голоса: {}",
        "whisper_not_installed": "⚠️ Для ускорения работы установи Whisper: pip install openai-whisper\nСейчас используется медленная альтернатива Google Speech Recognition",
    }

    def __init__(self):
        self.db = None
        self.recognizer = sr.Recognizer()
        self.whisper_model = None

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if not self.db.get("VoiceToText", "chats"):
            self.db.set("VoiceToText", "chats", {})
        
        if not WHISPER_AVAILABLE:
            print(self.strings["whisper_not_installed"])
        
        if WHISPER_AVAILABLE and not self.whisper_model:
            try:
                self.whisper_model = whisper.load_model("tiny")
            except:
                pass

    async def vttcmd(self, message):
        """Расшифровать голосовое сообщение"""
        if not message.is_reply:
            await utils.answer(message, "❌ Ответь на голосовое сообщение!")
            return
        reply = await message.get_reply_message()
        await self.process_voice_message_with_timeout(message, reply)

    async def vttchatcmd(self, message):
        """Включить/выключить автораспознавание в чате"""
        chat_id = str(message.chat_id)
        chats = self.db.get("VoiceToText", "chats", {})
        current_status = chats.get(chat_id, False)
        new_status = not current_status
        chats[chat_id] = new_status
        self.db.set("VoiceToText", "chats", chats)
        status_text = "включено" if new_status else "отключено"
        await utils.answer(message, f"✅ Автораспознавание голоса {status_text} в этом чате")

    async def process_voice_message_with_timeout(self, processing_msg, voice_message):
        processing_active = {"active": True, "partial_text": ""}
        
        async def timeout_handler():
            await asyncio.sleep(60.0)
            if processing_active["active"]:
                processing_active["active"] = False
                partial_text = processing_active["partial_text"].strip()
                timeout_text = partial_text if partial_text else "Распознавание не завершено"
                
                try:
                    await utils.answer(
                        processing_msg,
                        self.strings["timeout_error"].format(timeout_text),
                        reply_to=voice_message.id
                    )
                except:
                    try:
                        await processing_msg.delete()
                        await voice_message.reply(self.strings["timeout_error"].format(timeout_text))
                    except:
                        pass
        
        timeout_task = asyncio.create_task(timeout_handler())
        
        try:
            await self.process_voice_message_streaming(processing_msg, voice_message, processing_active)
            processing_active["active"] = False
            timeout_task.cancel()
        except Exception as e:
            processing_active["active"] = False
            timeout_task.cancel()
            raise e

    async def process_voice_message_streaming(self, processing_msg, voice_message, processing_active):
        try:
            if not any([voice_message.voice, voice_message.audio]):
                await utils.answer(processing_msg, self.strings["no_voice"])
                return

            await utils.answer(processing_msg, self.strings["processing"])

            file = await voice_message.download_media()
            if not file:
                await utils.answer(processing_msg, self.strings["download_error"])
                return

            wav_file = await self.convert_to_wav(file)
            os.remove(file)

            audio_segments = await self.split_audio_into_chunks(wav_file, chunk_duration=5)
            
            full_text = ""
            last_update_time = asyncio.get_event_loop().time()
            chunks_processed = 0
            
            for i, chunk_file in enumerate(audio_segments, 1):
                if not processing_active["active"]:
                    for remaining_chunk in audio_segments[i-1:]:
                        if os.path.exists(remaining_chunk):
                            os.remove(remaining_chunk)
                    break
                    
                try:
                    chunk_text = await self.recognize_speech_chunk(chunk_file)
                    
                    if chunk_text.strip() and not chunk_text.startswith("❌"):
                        full_text += chunk_text + " "
                        processing_active["partial_text"] = full_text
                    
                    os.remove(chunk_file)
                    chunks_processed += 1
                    
                    current_time = asyncio.get_event_loop().time()
                    should_update = (current_time - last_update_time >= 5.0) or (chunks_processed == 1 and full_text.strip())
                    
                    if should_update and full_text.strip() and processing_active["active"]:
                        try:
                            await utils.answer(
                                processing_msg,
                                f"🔊 Я распознал<blockquote>{full_text.strip()}</blockquote>"
                            )
                            last_update_time = current_time
                        except:
                            pass
                    
                except Exception as e:
                    if os.path.exists(chunk_file):
                        os.remove(chunk_file)
                    continue

            os.remove(wav_file)
            
            if processing_active["active"]:
                final_text = full_text.strip() or "❌ Речь не распознана"
                
                try:
                    await utils.answer(
                        processing_msg,
                        self.strings["result"].format(final_text),
                        reply_to=voice_message.id
                    )
                except:
                    try:
                        await processing_msg.delete()
                        await voice_message.reply(self.strings["result"].format(final_text))
                    except:
                        pass
                
        except Exception as e:
            if processing_active["active"]:
                try:
                    await utils.answer(processing_msg, self.strings["recognition_error"].format(str(e)))
                except:
                    try:
                        await processing_msg.delete()
                        await voice_message.reply(self.strings["recognition_error"].format(str(e)))
                    except:
                        pass

    async def split_audio_into_chunks(self, wav_file, chunk_duration=5):
        try:
            audio = AudioSegment.from_wav(wav_file)
            chunk_length_ms = chunk_duration * 1000
            chunks = []
            
            for i in range(0, len(audio), chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                chunk_file = f"{wav_file}_chunk_{i//chunk_length_ms}.wav"
                chunk.export(chunk_file, format="wav")
                chunks.append(chunk_file)
            
            return chunks
        except Exception as e:
            raise Exception(f"Ошибка разбиения аудио: {str(e)}")

    async def convert_to_wav(self, input_file):
        try:
            output_file = input_file + ".wav"
            audio = AudioSegment.from_file(input_file)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(output_file, format="wav")
            return output_file
        except Exception as e:
            raise Exception(self.strings["convert_error"] + ": " + str(e))

    async def recognize_speech_chunk(self, wav_file):
        try:
            if WHISPER_AVAILABLE and self.whisper_model:
                result = self.whisper_model.transcribe(
                    wav_file, 
                    language="ru",
                    fp16=False,
                    verbose=False
                )
                return result.get("text", "").strip() or ""
            else:
                with sr.AudioFile(wav_file) as source:
                    self.recognizer.energy_threshold = 300
                    self.recognizer.dynamic_energy_threshold = False
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                    return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return f"❌ Ошибка сервиса: {str(e)}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    async def recognize_speech(self, wav_file):
        return await self.recognize_speech_chunk(wav_file)

    async def watcher(self, message):
        chat_id = str(message.chat_id)
        if not self.db.get("VoiceToText", "chats", {}).get(chat_id, False):
            return
        if any([message.voice, message.audio]):
            try:
                processing_msg = await message.reply(self.strings["processing"])
                await self.process_voice_message_with_timeout(processing_msg, message)
            except Exception as e:
                await message.reply(self.strings["recognition_error"].format(str(e)))
