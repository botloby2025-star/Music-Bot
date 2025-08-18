import logging
import asyncio
from collections import deque
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioPiped, Update as PyTgCallsUpdate
from pytgcalls.types.stream import StreamAudioEnded
import yt_dlp

import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# --- लॉगिंग कॉन्फ़िगरेशन ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# क्लाइंट्स को इनिशियलाइज़ करें
app = PyTgCalls(api_id=API_ID, api_hash=API_HASH)
application = Application.builder().token(BOT_TOKEN).build()

# --- स्टेट मैनेजमेंट के लिए डिक्शनरी ---
chat_queues = {}
now_playing_message = {} 

# --- हेल्पर फंक्शन ---

def format_duration(seconds: int) -> str:
    if seconds is None: return "N/A"
    return str(datetime.timedelta(seconds=seconds)).lstrip("0:")

def create_now_playing_keyboard(is_paused: bool = False) -> InlineKeyboardMarkup:
    pause_resume_button = InlineKeyboardButton("▶️ Resume", callback_data="resume") if is_paused else InlineKeyboardButton("⏸️ Pause", callback_data="pause")
    keyboard = [[
        pause_resume_button,
        InlineKeyboardButton("⏭️ Skip", callback_data="skip"),
        InlineKeyboardButton("⏹️ Stop", callback_data="stop"),
    ]]
    return InlineKeyboardMarkup(keyboard)

async def play_next_song(chat_id: int):
    if chat_id in now_playing_message and now_playing_message[chat_id]:
        try:
            await application.bot.delete_message(chat_id, now_playing_message[chat_id])
        except Exception as e:
            logger.warning(f"पुराना मैसेज डिलीट नहीं कर सका: {e}")

    if chat_id in chat_queues and chat_queues[chat_id]:
        song_info = chat_queues[chat_id].popleft()
        try:
            await app.change_stream(chat_id, AudioPiped(song_info['url']))
            caption = (
                f"💎 **STARTED STREAMING**\n\n"
                f"◎ **TITLE :** [{song_info['title']}]({song_info['webpage_url']})\n"
                f"◎ **DURATION :** {format_duration(song_info['duration'])} MINUTES\n"
                f"◎ **REQUESTED BY :** {song_info['requester']}"
            )
            keyboard = create_now_playing_keyboard()
            sent_message = await application.bot.send_photo(
                chat_id=chat_id,
                photo=song_info['thumbnail'],
                caption=caption,
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
            now_playing_message[chat_id] = sent_message.message_id
        except Exception as e:
            logger.error(f"अगला गाना बजाने में त्रुटि: {e}")
            await application.bot.send_message(chat_id, f"गाना बजाने में कोई समस्या हुई: {e}")
    else:
        await app.leave_group_call(chat_id)
        if chat_id in now_playing_message:
            del now_playing_message[chat_id]

# --- PyTgCalls इवेंट हैंडलर ---
@app.on_stream_end()
async def on_stream_end_handler(_, update: PyTgCallsUpdate):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        await play_next_song(chat_id)

# --- टेलीग्राम बॉट कमांड और बटन हैंडलर्स ---

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    requester = update.message.from_user.mention_markdown()
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("कृपया गाने का नाम या यूट्यूब लिंक दें।")
        return
    await update.message.reply_text("🔄 प्रोसेसिंग...")
    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
    try:
        is_url = query.startswith("http")
        search_query = query if is_url else f"ytsearch:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info: info = info['entries'][0]
        song_info = {
            'url': info['url'], 'title': info.get('title', 'Unknown Title'),
            'duration': info.get('duration'), 'thumbnail': info.get('thumbnail'),
            'webpage_url': info.get('webpage_url'), 'requester': requester,
        }
        if chat_id not in chat_queues:
            chat_queues[chat_id] = deque()
        chat_queues[chat_id].append(song_info)
        await update.message.reply_text(f"✅ **{song_info['title']}** को क्यू में जोड़ा गया।")
        call_info = await app.get_call(chat_id)
        if not call_info.is_active:
             await play_next_song(chat_id)
    except Exception as e:
        logger.error(f"खोजने या जोड़ने में त्रुटि: {e}")
        await update.message.reply_text("माफ़ करें, गाना खोजने या क्यू में जोड़ने में कोई समस्या हुई।")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    action = query.data

    if action == "pause":
        await app.pause_stream(chat_id)
        keyboard = create_now_playing_keyboard(is_paused=True)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif action == "resume":
        await app.resume_stream(chat_id)
        keyboard = create_now_playing_keyboard(is_paused=False)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif action == "skip":
        await play_next_song(chat_id)

    elif action == "stop":
        if chat_id in chat_queues:
            chat_queues[chat_id].clear()
        await app.leave_group_call(chat_id)
        
        # <<<--- यहाँ बदलाव किया गया है ---<<<
        # मैसेज को डिलीट करने के बजाय, उसे एडिट करें
        try:
            # कैप्शन को अपडेट करें
            original_caption = query.message.caption
            new_caption = original_caption.replace("💎 STARTED STREAMING", "⏹️ STREAM ENDED")
            
            # मैसेज को नए कैप्शन के साथ एडिट करें और बटन हटा दें
            await query.edit_message_caption(
                caption=new_caption,
                reply_markup=None  # reply_markup=None करने से बटन हट जाते हैं
            )
        except Exception as e:
            logger.warning(f"स्टॉप पर मैसेज एडिट नहीं कर सका: {e}")
            # अगर किसी कारण से कैप्शन एडिट नहीं हो पाता है, तो कम से कम बटन हटा दें
            await query.edit_message_reply_markup(reply_markup=None)
        
        # अब जब म्यूजिक बंद हो गया है, तो इस चैट के लिए now_playing_message की जरूरत नहीं है
        if chat_id in now_playing_message:
            del now_playing_message[chat_id]

# मेन फंक्शन
async def main():
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    await app.start()
    print("बॉट सफलतापूर्वक शुरू हो गया है!")
    await asyncio.gather(application.run_polling(), idle())

if __name__ == "__main__":
    asyncio.run(main())