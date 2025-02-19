# (©) CodeXBotz

import os
import asyncio
from random import choice
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, START_PIC, AUTO_DELETE_TIME, AUTO_DELETE_MSG, JOIN_REQUEST_ENABLE, FORCE_SUB_CHANNEL
from helper_func import subscribed, decode, get_messages, delete_file
from database.database import add_user, del_user, full_userbase, present_user

# List of start emojis
START_EMOJIS = ["🚀", "🔥", "💥", "⚡", "✨", "🎯"]

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Add user if not present
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except:
            pass

    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except:
            return
        decoded_string = await decode(base64_string)
        argument = decoded_string.split("-")

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            ids = range(start, end + 1) if start <= end else list(reversed(range(end, start + 1)))
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return

        temp_msg = await message.reply("Please wait...")

        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return

        await temp_msg.delete()
        track_msgs = []

        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name)
                       if bool(CUSTOM_CAPTION) and bool(msg.document) else
                       ("" if not msg.caption else msg.caption.html))

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            if AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0:
                try:
                    copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg:
                        track_msgs.append(copied_msg)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg:
                        track_msgs.append(copied_msg)
                except Exception as e:
                    print(f"Error copying message: {e}")

            else:
                try:
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)

        if track_msgs:
            delete_data = await client.send_message(chat_id=message.from_user.id, text=AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME))
            asyncio.create_task(delete_file(track_msgs, client, delete_data))

        return

    # Random emoji for start message
    start_emoji = choice(START_EMOJIS)

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data="about"), InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])

    start_text = f"{start_emoji} {START_MSG.format(first=message.from_user.first_name, last=message.from_user.last_name, username=None if not message.from_user.username else '@' + message.from_user.username, mention=message.from_user.mention, id=message.from_user.id)}"

    if START_PIC:
        await message.reply_photo(photo=START_PIC, caption=start_text, reply_markup=reply_markup, quote=True)
    else:
        await message.reply_text(text=start_text, reply_markup=reply_markup, disable_web_page_preview=True, quote=True)


# Message for waiting and errors
WAIT_MSG = """<b>Processing ...</b>"""
REPLY_ERROR = """<code>Use this command as a reply to any telegram message without any spaces.</code>"""

@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    ButtonUrl = (await client.create_chat_invite_link(chat_id=FORCE_SUB_CHANNEL, creates_join_request=True)).invite_link if bool(JOIN_REQUEST_ENABLE) else client.invitelink

    buttons = [[InlineKeyboardButton("Join Channel", url=ButtonUrl)]]

    try:
        buttons.append([InlineKeyboardButton(text='Try Again', url=f"https://t.me/{client.username}?start={message.command[1]}")])
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(first=message.from_user.first_name, last=message.from_user.last_name, username=None if not message.from_user.username else '@' + message.from_user.username, mention=message.from_user.mention, id=message.from_user.id),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total, successful, blocked, deleted, unsuccessful = 0, 0, 0, 0, 0

        pls_wait = await message.reply("<i>Broadcasting Message... This will take some time.</i>")

        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1

            total += 1

        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""

        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
