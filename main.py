import discord
import json
import asyncio
import os
import logging

# --- Configuration (پێویستە ئەم زانیارییانە پڕ بکەیتەوە) ---
# تۆکنی بۆتە سەرەکییەکەمان کە هەموو فەرمانەکان بەڕێوە دەبات.
# ئەمە دەبێت تۆکنی بۆتێکی دیسکۆرد بێت کە لە Developer Portal دروستت کردووە.
MAIN_BOT_TOKEN = "" # : "YOUR_MAIN_BOT_TOKEN_HERE"

# ئایدی بەکارهێنەری تۆ (مەتین گیان)، بۆ کۆنترۆڵی تەنها خۆت لەسەر بۆتەکە.
# دەتوانیت ئایدییەکەت بدۆزیتەوە بە Enable کردنی Developer Mode لە دیسکۆرد، پاشان ڕاست کلیک بکەیت لەسەر ئەکاونتەکەت و Copy ID دابگریت.
OWNER_ID = 918195315625062431 # نموونە: OWNER_ID_HERE (تکایە بیگۆڕە بۆ ئایدییەکەی خۆت)

DATABASE_FILE = 'database.json'
# ئەم دیکشنەرییە بۆ هەڵگرتنی کلایەنتە چالاکەکانی هەموو ئەکاونتە زیادکراوەکانە.
# کلی (key) ئایدی ئەکاونتەکە دەبێت و بەهاکەی (value) ئۆبجێکتی discord.Clientـەکەیە.
active_sub_clients = {}

# --- Logger Setup (بۆ تۆمارکردنی زانیاری و هەڵەکان) ---
# یارمەتیدەرە بۆ ئەوەی بزانین چی ڕوودەدات لە کاتی کارکردنی بۆتەکەدا
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Functions (فەنکشنەکانی کارکردن لەگەڵ داتابەیس) ---

# فەنکشنێک بۆ خوێندنەوەی داتا لە فایلی database.json
def load_database():
    if not os.path.exists(DATABASE_FILE):
        # ئەگەر فایلەکە نەبوو، فایلێکی نوێ دروست دەکەین بە پێکهاتەی سەرەتایی.
        initial_data = {"owner_id": OWNER_ID, "accounts": []}
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=4)
        logger.info(f"فایلی '{DATABASE_FILE}' دروست کرا و داتای سەرەتایی تێدا دانرا.")
        return initial_data
    
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            # دڵنیابوونەوە لەوەی پێکهاتەی بنەڕەتی هەیە
            if "owner_id" not in data:
                data["owner_id"] = OWNER_ID
                save_database(data)
            if "accounts" not in data:
                data["accounts"] = []
                save_database(data)
            return data
        except json.JSONDecodeError:
            # ئەگەر فایلەکە خاڵی بوو یان کۆدەکەی هەڵە بوو (وەک {}, بەڵام شتێکی تر هەڵەیە)
            logger.error(f"هەڵە لە خوێندنەوەی فایلی '{DATABASE_FILE}'. فایلەکە پووچەڵ دەکەینەوە و داتای سەرەتایی تێدا دادەنێین.")
            initial_data = {"owner_id": OWNER_ID, "accounts": []}
            with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=4)
            return initial_data

# فەنکشنێک بۆ پاشەکەوتکردنی داتا لە فایلی database.json
def save_database(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4) # indent=4 بۆ ئەوەی فایلەکە جوانتر و ڕێکتر دەربکەوێت
    logger.info(f"داتا پاشەکەوت کرا بۆ '{DATABASE_FILE}'.")

# --- Main Discord Bot Setup (ڕێکخستنی بۆتە سەرەکییەکەمان) ---
# Intentsـەکانی Discord بۆ ڕێگەدان بە بۆتەکەمان کە چ جۆرە ڕووداوێک ببینێت.
intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True
intents.members = True 

main_bot_client = discord.Client(intents=intents)

# --- Sub-Bot (Account) Management Functions (فەنکشنەکانی بەڕێوەبردنی ئەکاونتەکان) ---

# فەنکشنێک بۆ وەرگرتنی ID و Usernameی ئەکاونتێک لە تۆکنەکەیەوە (بۆ تێستکردن و زانیاریی سەرەتایی)
async def get_bot_info_from_token(test_token):
    test_client = discord.Client(intents=intents)
    id_holder = None
    username_holder = None

    @test_client.event
    async def on_ready():
        nonlocal id_holder, username_holder
        id_holder = str(test_client.user.id)
        username_holder = str(test_client.user) # Gets username#discriminator
        logger.info(f"تۆکنی کاتی سەرکەوتوو بوو. ID ئەکاونت: {id_holder}, Username: {username_holder}")
        await test_client.close()
    
    try:
        # لێرەدا 'bot=' لابراوە وەک باسمان کرد بۆ چارەسەرکردنی هەڵەی 'unexpected keyword argument bot'
        await test_client.start(test_token) 
    except discord.LoginFailure:
        logger.error(f"تۆکنەکە هەڵەیە یان نەگونجاوە (LoginFailure).")
        id_holder = "INVALID_TOKEN"
    except Exception as e:
        logger.error(f"هەڵەیەکی نەزانراو لە کاتی تێستکردنی تۆکن: {e}", exc_info=True)
        id_holder = "ERROR"
    finally:
        if not test_client.is_closed(): # دڵنیابوونەوە لەوەی clientـەکە داخراوە تەنانەت ئەگەر هەڵەش ڕوویدا
            await test_client.close()
    return id_holder, username_holder

# ئەمە فەنکشنە گرنگەکەیە بۆ ئۆنلاینکردنی هەر ئەکاونتێک کە زیاد دەکرێت.
async def start_sub_client(account_data):
    user_id = account_data['user_id']
    full_token = account_data['full_token']
    username = account_data.get('username', user_id) # ئەگەر username نەبوو، user_id بەکار دەهێنێت

    # پشکنین بۆ ئەوەی بزانین کلایەنتەکە پێشتر دروست نەکراوە بۆ ئەم user_idـیە و چالاک نییە
    if user_id in active_sub_clients and not active_sub_clients[user_id].is_closed():
        if active_sub_clients[user_id].is_ready():
            logger.warning(f"ئەکاونتی {username} ({user_id}) پێشتر چالاکە و ئۆنلاینە. ستاتسی داتابەیس نوێ دەکەینەوە ئەگەر پێویست بێت.")
            db_data = load_database()
            for acc in db_data['accounts']:
                if acc['user_id'] == user_id and acc['status'] != 'online':
                    acc['status'] = 'online'
                    save_database(db_data)
                    logger.info(f"ستاتسی ئەکاونتی '{username}' ({user_id}) لە داتابەیسدا نوێ کرایەوە بۆ 'online'.")
                break
            return active_sub_clients[user_id]
        else:
            logger.warning(f"ئەکاونتی {username} ({user_id}) کلایەنتەکەی هەیە بەڵام ئامادە نییە. هەوڵدەدەین دووبارە دەستی پێبکەینەوە.")
            await stop_sub_client(user_id) # سەرەتا کلایەنتە کۆنەکە ڕادەگرین ئەگەر ئامادە نەبوو
            # پاشان بەردەوام دەبین بۆ دروستکردنی کلایەنتێکی نوێ.

    sub_client = discord.Client(intents=intents)

    @sub_client.event
    async def on_ready():
        logger.info(f"ئەکاونتی خوارەوە (Sub-Bot) '{sub_client.user}' ئۆنلاین بوو! ID: {sub_client.user.id}")
        # گۆڕینی ستاتس بۆ "مۆبایل"
        await sub_client.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name='Mobile', type=discord.ActivityType.playing), # Playing 'Mobile'
        )
        logger.info(f"ستاتسی ئەکاونتی '{sub_client.user}' دانرا بە 'Mobile'.")
        
        # نوێکردنەوەی داتابەیس بۆ نیشاندانی ستاتسی "online"
        db_data = load_database()
        for acc in db_data['accounts']:
            if acc['user_id'] == str(sub_client.user.id):
                acc['status'] = 'online'
                acc['is_mobile'] = True
                if acc.get('username') != str(sub_client.user): # نوێکردنەوەی username ئەگەر گۆڕابوو
                    acc['username'] = str(sub_client.user)
                break
        save_database(db_data)
        active_sub_clients[user_id] = sub_client # لێرەدا دەخرێتە ناو active_sub_clients تا دڵنیا بین کە سەرکەوتوو بووە

    try:
        logger.info(f"هەوڵدان بۆ ئۆنلاینکردنی ئەکاونتی {username} ({user_id})...")
        # لێرەدا 'bot=' لابراوە وەک باسمان کرد
        await sub_client.start(full_token)
        return sub_client
    except discord.LoginFailure:
        logger.error(f"هەڵە لە چوونەژوورەوە بۆ ئەکاونتی {username} ({user_id}). تۆکنەکە هەڵەیە یان نەگونجاوە (LoginFailure).")
        # ستاتسی ئەکاونتەکە لە داتابەیسدا نوێ دەکەینەوە
        db_data = load_database()
        for acc in db_data['accounts']:
            if acc['user_id'] == user_id:
                acc['status'] = 'invalid_token'
                break
        save_database(db_data)
        if user_id in active_sub_clients: # لە لیستی چالاکەکان لادەبرێت ئەگەر چوونەژوورەوە سەرکەوتوو نەبوو
            del active_sub_clients[user_id]
        return None
    except Exception as e:
        logger.error(f"هەڵەیەکی نەزانراو ڕوویدا لە کاتی ئۆنلاینکردنی ئەکاونتی {username} ({user_id}): {e}", exc_info=True)
        db_data = load_database()
        for acc in db_data['accounts']:
            if acc['user_id'] == user_id:
                acc['status'] = 'error'
                break
        save_database(db_data)
        if user_id in active_sub_clients:
            del active_sub_clients[user_id]
        return None

# فەنکشنێک بۆ وەستاندنی هەر ئەکاونتێکی ژێرەوە
async def stop_sub_client(user_id):
    if user_id in active_sub_clients:
        sub_client = active_sub_clients[user_id]
        if not sub_client.is_closed():
            try:
                await sub_client.close()
                logger.info(f"ئەکاونتی خوارەوە (Sub-Bot) '{user_id}' ڕاگیرا.")
            except Exception as e:
                logger.error(f"هەڵە لە ڕاگرتنی ئەکاونتی '{user_id}': {e}", exc_info=True)
        del active_sub_clients[user_id]
        
        # نوێکردنەوەی داتابەیس بۆ نیشاندانی ستاتسی "offline"
        db_data = load_database()
        for acc in db_data['accounts']:
            if acc['user_id'] == user_id:
                acc['status'] = 'offline'
                break
        save_database(db_data)
        return True
    logger.warning(f"ئەکاونتی {user_id} نەدۆزرایەوە لە لیستی کلایەنتە چالاکەکاندا بۆ ڕاگرتن.")
    return False


# --- Main Bot Events (ڕووداوەکانی بۆتە سەرەکییەکە) ---

@main_bot_client.event
async def on_ready():
    logger.info(f"بۆتە سەرەکییەکەمان '{main_bot_client.user}' ئۆنلاین بوو! ID: {main_bot_client.user.id}")
    logger.info(f"ئاریا ئێستا خزمەت بە مەتین گیان دەکات. پڕۆژەی ئەکاونتی دیسکۆرد لە ڕێکەوتی 2026-05-01 چالاک کرا.")

    # کاتێک بۆتە سەرەکییەکە ئۆنلاین دەبێت، هەموو ئەکاونتە پاشەکەوتکراوەکان دەخوێنێتەوە و ئۆنلاینیان دەکات.
    db_data = load_database()
    if 'accounts' in db_data:
        for account in db_data['accounts']:
            if account.get('full_token'): # تەنها ئەو ئەکاونتانە ئۆنلاین دەکەین کە تۆکنی تەواویان هەیە
                logger.info(f"هەوڵدان بۆ ئۆنلاینکردنی ئەکاونتی '{account.get('username', account['user_id'])}' ({account['user_id']}) لە داتابەیسەوە...")
                # فەنکشنی start_sub_client وای لێدەکەین کە لە پاشبنەما کار بکات (background task)
                # تاوەکو نەبێتە هۆی بلۆککردنی on_ready.
                main_bot_client.loop.create_task(start_sub_client(account))
    else:
        logger.info("هیچ ئەکاونتێک لە داتابەیسدا نەدۆزرایەوە.")

@main_bot_client.event
async def on_message(message):
    # دڵنیابوونەوە لەوەی نامەکە لەلایەن بۆتەکەوە نەنێردراوە بۆ خۆی یان بۆتێکی تر
    if message.author == main_bot_client.user or message.author.bot: 
        return

    # دڵنیابوونەوە لەوەی تەنها مەتین گیان دەتوانێت فەرمانەکان جێبەجێ بکات
    if message.author.id != OWNER_ID:
        await message.channel.send("ببوورە مەتین گیان، تەنها خاوەنی بۆتەکە دەتوانێت فەرمانەکان جێبەجێ بکات.")
        return

    # پشکنینی فەرمانەکان (بەم کۆماندانە دەست پێدەکات)
    if message.content.startswith('/add_account'):
        await add_account_command(message)
    elif message.content.startswith('/remove_account'):
        await remove_account_command(message)
    elif message.content.startswith('/list_accounts'):
        await list_accounts_command(message)
    elif message.content.startswith('/list_account_servers'):
        await list_account_servers_command(message)
    elif message.content.startswith('/leave_server'):
        await leave_server_command(message)
    elif message.content.startswith('/help'):
        await help_command(message)
    # لێرەدا کۆماندەکانی تریش زیاد دەکەین:
    # elif message.content.startswith('/join_server'): # ئەمە تەنها وەک placeholder دانراوە
    #     await join_server_command(message)


# --- Command Implementations (جێبەجێکردنی فەرمانەکان) ---

async def add_account_command(message):
    parts = message.content.split(' ')
    if len(parts) < 2:
        await message.channel.send("مەتین گیان، فەرمانی `/add_account` پێویستی بە تۆکنی ئەکاونت هەیە. فەرموو، بەم شێوەیە بەکاری بهێنە: `/add_account <تۆکنی_ئەکاونت>`")
        return

    token = parts[1]
    
    # بۆ پاراستنی تۆکنەکە، تەنها بەشێکی لێ نیشان دەدەین
    display_token = token[:5] + "..." + token[-5:] if len(token) > 10 else token
    await message.channel.send(f"مەتین گیان، تۆکنەکە وەرگیرا: `{display_token}`. لە هەوڵی زیادکردنی ئەکاونتەکەدام...")
    logger.info(f"وەرگرتنی داواکاری بۆ زیادکردنی ئەکاونت بە تۆکنی: {display_token}")

    # وەرگرتنی ID و Username لە تۆکنەکە
    user_id, username = await get_bot_info_from_token(token)

    if user_id == "INVALID_TOKEN":
        await message.channel.send("مەتین گیان، ئەم تۆکنە هەڵەیە یان نەگونجاوە. تکایە دڵنیابەوە لە تۆکنی بۆتێک بێت (نەک تۆکنی بەکارهێنەر).")
        return
    elif user_id == "ERROR":
        await message.channel.send("مەتین گیان، هەڵەیەکی نەزانراو لە کاتی تێستکردنی تۆکنەکە ڕوویدا. تکایە دووبارە هەوڵ بدەوە.")
        return
    elif not user_id:
        await message.channel.send("مەتین گیان، نەتوانرا ئایدی و ناوی ئەکاونتەکە بە دەست بێت. لەوانەیە کێشەی پەیوەندی هەبێت.")
        return

    # پشکنین بۆ ئەوەی بزانین ئایا ئەکاونتەکە پێشتر زیاد کراوە
    db_data = load_database()
    for acc in db_data['accounts']:
        if acc['user_id'] == user_id:
            await message.channel.send(f"مەتین گیان، ئەکاونتی `{username}` (ID: `{user_id}`) پێشتر زیاد کراوە! ستاتسی ئێستای: `{acc['status']}`")
            if acc['status'] != 'online' or user_id not in active_sub_clients: # ئەگەر ئۆنلاین نەبوو، هەوڵدەدەین ئۆنلاینی بکەین
                await message.channel.send(f"ئەکاونتەکە پێشتر هەیە بەڵام ئۆنلاین نییە یان کلایەنتەکەی چالاک نییە، هەوڵدەدەین ئۆنلاینی بکەینەوە...")
                sub_client_obj = await start_sub_client(acc)
                if sub_client_obj:
                    await message.channel.send(f"ئەکاونتی `{username}` (ID: `{user_id}`) بە سەرکەوتوویی ئۆنلاین کرایەوە!")
                else:
                    await message.channel.send(f"هەڵە لە ئۆنلاینکردنەوەی ئەکاونتی `{username}` (ID: `{user_id}`). تکایە تۆکنەکە بپشکنە.")
            return

    # ئەگەر ئەکاونتەکە نوێ بوو، زیادیدەکەین
    new_account = {
        "index": len(db_data['accounts']) + 1, # بۆ ئاسانکاری لە ناسینەوە
        "user_id": user_id,
        "username": username,
        "token": display_token, # تەنها بەشێکی بچووک بۆ نیشاندان
        "full_token": token,    # تۆکنی تەواو بۆ بەکارهێنان
        "status": "offline",    # سەرەتا وەک ئۆفلاین دیاری دەکرێت تا ئۆنلاین دەکرێت
        "is_mobile": True,      # دڵنیایی لەوەی مەبەستمانە ستاتسی مۆبایل بێت
    }
    db_data['accounts'].append(new_account)
    save_database(db_data)

    await message.channel.send(f"مەتین گیان، ئەکاونتی `{username}` (ID: `{user_id}`) بە سەرکەوتوویی زیاد کرا بۆ داتابەیس. ئێستا لە هەوڵی ئۆنلاینکردنیدام...")
    
    # یەکسەر ئەکاونتە نوێیەکە ئۆنلاین دەکەین
    sub_client_obj = await start_sub_client(new_account)

    if sub_client_obj:
        await message.channel.send(f"ئەکاونتی `{sub_client_obj.user}` بە سەرکەوتوویی ئۆنلاین کرا بە ستاتسی مۆبایل!")
    else:
        await message.channel.send(f"هەڵە لە ئۆنلاینکردنی ئەکاونتی `{username}` (ID: `{user_id}`). تکایە دڵنیابەوە لە تۆکنەکە یان پەیوەندیی ئینتەرنێت.")

async def remove_account_command(message):
    parts = message.content.split(' ')
    if len(parts) < 2:
        await message.channel.send("مەتین گیان، فەرمانی `/remove_account` پێویستی بە IDـی ئەکاونت هەیە. فەرموو، بەم شێوەیە بەکاری بهێنە: `/remove_account <ئایدی_ئەکاونت>`")
        return

    target_user_id = parts[1]
    
    db_data = load_database()
    accounts_to_keep = []
    removed_account_name = None
    account_found = False

    for acc in db_data['accounts']:
        if acc['user_id'] == target_user_id:
            account_found = True
            removed_account_name = acc.get('username', acc['user_id'])
            # سەرەتا کلایەنتەکە ڕادەگرین ئەگەر چالاک بوو
            if target_user_id in active_sub_clients:
                await stop_sub_client(target_user_id)
            logger.info(f"ئەکاونتی '{removed_account_name}' (ID: `{target_user_id}`) لە داتابەیس لادەبرێت.")
        else:
            accounts_to_keep.append(acc)
    
    if account_found:
        db_data['accounts'] = accounts_to_keep
        save_database(db_data)
        await message.channel.send(f"مەتین گیان، ئەکاونتی `{removed_account_name}` (ID: `{target_user_id}`) بە سەرکەوتوویی لابرا و ڕاگیرا.")
    else:
        await message.channel.send(f"مەتین گیان، ئەکاونتێک بە ئایدی `{target_user_id}` نەدۆزرایەوە.")

async def list_accounts_command(message):
    db_data = load_database()
    accounts = db_data['accounts']

    if not accounts:
        await message.channel.send("مەتین گیان، هیچ ئەکاونتێک زیاد نەکراوە.")
        return

    response_message = "مەتین گیان، لیستی ئەکاونتە زیادکراوەکان:\n"
    for acc in accounts:
        status_emoji = "✅ ئۆنلاین" if acc['status'] == 'online' else ("❌ ئۆفلاین" if acc['status'] == 'offline' else "⚠️ " + acc['status'])
        response_message += f"**{acc.get('username', 'نادیار')}** (ID: `{acc['user_id']}`) - ستاتس: {status_emoji}\n"
    
    if len(response_message) > 2000:
        await message.channel.send("مەتین گیان، لیستی ئەکاونتەکان زۆر درێژە، تەنها بەشی سەرەتایی نیشان دەدەم.")
        await message.channel.send(response_message[:1990] + "...")
    else:
        await message.channel.send(response_message)

async def list_account_servers_command(message):
    parts = message.content.split(' ')
    if len(parts) < 2:
        await message.channel.send("مەتین گیان، فەرمانی `/list_account_servers` پێویستی بە IDـی ئەکاونت هەیە. فەرموو، بەم شێوەیە بەکاری بهێنە: `/list_account_servers <ئایدی_ئەکاونت>`")
        return

    target_user_id = parts[1]

    sub_client = active_sub_clients.get(target_user_id)

    if not sub_client or not sub_client.is_ready():
        # پشکنین بۆ ئەوەی بزانین ئایا ئەکاونتەکە لە داتابەیسدا هەیە بەڵام ئۆنلاین نییە.
        db_data = load_database()
        found_in_db = False
        for acc in db_data['accounts']:
            if acc['user_id'] == target_user_id:
                found_in_db = True
                username = acc.get('username', target_user_id)
                if acc['status'] == 'offline':
                    await message.channel.send(f"مەتین گیان، ئەکاونتی `{username}` (ID: `{target_user_id}`) لە داتابەیسدا هەیە بەڵام ئێستا ئۆفلاینە.")
                elif acc['status'] == 'online' and not sub_client: # وەک online دیاریکراوە بەڵام clientـەکە چالاک نییە
                    await message.channel.send(f"مەتین گیان، ئەکاونتی `{username}` (ID: `{target_user_id}`) لە داتابەیسدا وەک ئۆنلاین دیاریکراوە، بەڵام کلایەنتەکەی چالاک نییە. لەوانەیە هەڵەیەکی تێدا ڕوویدابێت.")
                else: # هەر ستاتسێکی تر
                    await message.channel.send(f"مەتین گیان، ئەکاونتی `{username}` (ID: `{target_user_id}`) لە داتابەیسدا هەیە بەڵام ستاتسەکەی بریتییە لە: `{acc['status']}` و چالاک نییە.")
                return
        
        if not found_in_db:
            await message.channel.send(f"مەتین گیان، ئەکاونتێک بە ئایدی `{target_user_id}` نەدۆزرایەوە.")
        return

    guilds = sub_client.guilds
    
    if not guilds:
        await message.channel.send(f"مەتین گیان، ئەکاونتی `{sub_client.user}` (ID: `{target_user_id}`) لە هیچ سێرڤەرێکدا نییە.")
        return

    # دروستکردنی پەیامی وەڵام
    response_message = f"مەتین گیان، ئەکاونتی `{sub_client.user}` (ID: `{target_user_id}`) لەم سێرڤەرانەدا هەیە:\n"
    
    for i, guild in enumerate(guilds):
        response_message += f"{i+1}. **{guild.name}** (ID: `{guild.id}`)\n"
    
    # دڵنیابوونەوە لەوەی درێژی پەیامەکە لە ٢٠٠٠ پیت تێپەڕ ناکات
    if len(response_message) > 2000:
        await message.channel.send(response_message[:1990] + "...")
        await message.channel.send(f"**تێبینی:** لیستی تەواو زۆر درێژ بوو، ئەمە تەنها بەشێکیەتی.")
    else:
        await message.channel.send(response_message)

async def leave_server_command(message):
    parts = message.content.split(' ')
    if len(parts) < 3:
        await message.channel.send("مەتین گیان، فەرمانی `/leave_server` پێویستی بە IDـی سێرڤەر و ئایدی یەک یان زیاتر لە ئەکاونت هەیە. فەرموو، بەم شێوەیە بەکاری بهێنە: `/leave_server <ئایدی_سێرڤەر> <ئایدی_ئەکاونت_1> [ئایدی_ئەکاونت_2 ... یان 'all']`")
        return

    guild_id_str = parts[1]
    account_ids_to_leave = parts[2:]

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        await message.channel.send("مەتین گیان، IDـی سێرڤەرەکە دەبێت ژمارە بێت.")
        return

    db_data = load_database()
    all_accounts = db_data['accounts']
    
    if not all_accounts:
        await message.channel.send("مەتین گیان، هیچ ئەکاونتێک زیاد نەکراوە بۆ ئەوەی سێرڤەر جێبهێڵێت.")
        return

    target_accounts = []
    if 'all' in [id.lower() for id in account_ids_to_leave]:
        for acc in all_accounts:
            if acc['user_id'] in active_sub_clients and active_sub_clients[acc['user_id']].is_ready():
                target_accounts.append(acc['user_id'])
    else:
        for acc_id in account_ids_to_leave:
            found = False
            for acc in all_accounts:
                if acc['user_id'] == acc_id:
                    if acc_id in active_sub_clients and active_sub_clients[acc_id].is_ready():
                        target_accounts.append(acc_id)
                        found = True
                        break
                    else:
                        await message.channel.send(f"مەتین گیان، ئەکاونتی `{acc.get('username', acc_id)}` (ID: `{acc_id}`) چالاک نییە یان ئۆنلاین نییە بۆ جێهێشتنی سێرڤەر.")
                        found = True
                        break
            if not found:
                await message.channel.send(f"مەتین گیان، ئەکاونتێک بە ئایدی `{acc_id}` نەدۆزرایەوە لە داتابەیسدا.")

    if not target_accounts:
        await message.channel.send("مەتین گیان، هیچ ئەکاونتێکی چالاک و ئۆنلاین دیاری نەکرا بۆ جێهێشتنی سێرڤەر.")
        return

    success_count = 0
    failed_accounts = []
    
    await message.channel.send(f"مەتین گیان، هەوڵدەدەم {len(target_accounts)} ئەکاونت سێرڤەری `{guild_id}` جێبهێڵن...")

    for user_id in target_accounts:
        sub_client = active_sub_clients[user_id]
        guild = sub_client.get_guild(guild_id)
        if guild:
            try:
                await guild.leave()
                logger.info(f"ئەکاونتی '{sub_client.user}' (ID: `{user_id}`) سێرڤەری '{guild.name}' (ID: `{guild_id}`) جێهێشت.")
                success_count += 1
            except Exception as e:
                logger.error(f"هەڵە لە جێهێشتنی سێرڤەری '{guild_id}' لەلایەن ئەکاونتی '{user_id}': {e}", exc_info=True)
                failed_accounts.append(f"{sub_client.user} (ID: `{user_id}`) - {e}")
        else:
            failed_accounts.append(f"ئەکاونتی `{user_id}` لە سێرڤەری `{guild_id}`دا نەبوو.")
            logger.warning(f"ئەکاونتی `{user_id}` لە سێرڤەری `{guild_id}`دا نەبوو بۆ جێهێشتن.")

    response = f"مەتین گیان، پرۆسەی جێهێشتنی سێرڤەری `{guild_id}` تەواو بوو:\n"
    response += f"**{success_count}** ئەکاونت بە سەرکەوتوویی سێرڤەرەکەیان جێهێشت.\n"
    if failed_accounts:
        response += "**ئەمانە نەیانتوانی سێرڤەرەکە جێبهێڵن:**\n"
        for failure in failed_accounts:
            response += f"- {failure}\n"
    
    await message.channel.send(response)

# placeholder for join_server, due to bot token limitations
async def join_server_command(message):
    # ئەم کۆماندە تەنها وەک ڕوونکردنەوەیەک دانراوە چونکە ڕاستەوخۆ جۆینکردنی بۆتێک بۆ سێرڤەرێک
    # لە ڕێگەی invite linkـەوە، لەلایەن Discord APIـی بۆتەکانەوە پشتیوانی ناکرێت (بۆ User Accountsـە).
    # بۆتەکان پێویستە لە ڕێگەی OAuth2 Authorization URLـەوە بانگهێشت بکرێن.
    await message.channel.send(
        "مەتین گیان، ناتوانم فەرمانی `/join_server` بۆ بۆتەکان جێبەجێ بکەم بە شێوەی ڕاستەوخۆ بە بەکارهێنانی invite link. "
        "بۆتەکان پێویستە لە ڕێگەی OAuth2 Authorization URLـەوە بانگهێشت بکرێن. "
        "ئەگەر دەتەوێت بۆتێک زیاد بکەیت بۆ سێرڤەرێک، پێویستە OAuth2 Linkـەکەی بەکار بهێنیت."
    )

async def help_command(message):
    help_text = """
    مەتین گیان، فەرمانەکانی AnDex Bot:

    **`مەرجەکانی بەکارهێنان: تەنها خاوەنی بۆتەکە (تۆ) دەتوانیت ئەم فەرمانانە بەکار بهێنیت.`**
    **`هەموو ئەکاونتەکان دەبێت تۆکنی بۆت بن، نەک ئەکاونتی بەکارهێنەر.`**

    **`/add_account <تۆکنی_ئەکاونت>`**
    - ئەکاونتێکی بۆت زیاد دەکات بۆ داتابەیس و یەکسەر ئۆنلاینی دەکات بە ستاتسی مۆبایلەوە.

    **`/remove_account <ئایدی_ئەکاونت>`**
    - ئەکاونتێک لە داتابەیس و لە چالاکییەکانی بۆتەکە لادەبات و ئۆفلاینی دەکات.

    **`/list_accounts`**
    - لیستی هەموو ئەکاونتە زیادکراوەکان نیشان دەدات لەگەڵ ستاتسەکانیان.

    **`/list_account_servers <ئایدی_ئەکاونت>`**
    - لیستی ئەو سێرڤەرانە نیشان دەدات کە ئەکاونتە دیاریکراوەکە لەناوێتی.

    **`/leave_server <ئایدی_سێرڤەر> <ئایدی_ئەکاونت_1> [ئایدی_ئەکاونت_2 ... یان 'all']`**
    - ژمارەیەک ئەکاونت لە سێرڤەرێکی دیاریکراو دەردەکات (leaves the server).
    - بۆ نموونە: `/leave_server 123456789012345678 987654321098765432`
    - یان بۆ هەموو ئەکاونتە چالاکەکان: `/leave_server 123456789012345678 all`

    **`/help`**
    - ئەم پەیامی یارمەتییە نیشان دەدات.

    """
    await message.channel.send(help_text)


# --- Main execution (جێبەجێکردنی سەرەکی) ---
if __name__ == "__main__":
    # دڵنیابوونەوە لە پڕکردنەوەی TOKEN و OWNER_ID
    if MAIN_BOT_TOKEN == "لێرە تۆکنی بۆتە سەرەکییەکەت دابنێ" or OWNER_ID == 123456789012345678:
        logger.error("تکایە MAIN_BOT_TOKEN و OWNER_ID پڕ بکەرەوە لە سەرەتای فایلی main.py!")
        print("تکایە MAIN_BOT_TOKEN و OWNER_ID پڕ بکەرەوە لە سەرەتای فایلی main.py!")
        exit() # لە کارکردن دەوەستێت

    # ڕێکخستنی Logging بۆ discord.py
    discord.utils.setup_logging(level=logging.INFO, root=False)

    try:
        main_bot_client.run(MAIN_BOT_TOKEN)
    except discord.LoginFailure:
        logger.error("هەڵە لە چوونەژوورەوە بۆ بۆتە سەرەکییەکە. تکایە دڵنیابەوە لە MAIN_BOT_TOKEN.")
    except Exception as e:
        logger.error(f"هەڵەیەکی نەزانراو ڕوویدا لە کاتی کارکردنی بۆتە سەرەکییەکە: {e}", exc_info=True)
