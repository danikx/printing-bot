import os
import aiohttp
import asyncpg
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import tempfile
from config import TELEGRAM_BOT_TOKEN, USER_SPECIFIC_ID, MINI_PRINTER
import asyncio
import re 
import urllib.parse
import logging
import hashlib
from print_file import print_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

whitelisted_users = [
    USER_SPECIFIC_ID, 
]

document_queue = {}

def sanitize_filename(filename: str) -> str:
    # Remove any non-alphanumeric characters except for dots and dashes
    clean_name = re.sub(r'[^\w\-\.]', '_', filename)
    # URL encode the filename to handle special characters
    return urllib.parse.quote(clean_name)

async def is_authorized(telegram_id: int) -> bool:
    logger.info(f"Checking authorization for user {telegram_id}")
    return telegram_id in whitelisted_users

async def log_download(telegram_id: int, torrent_hash: str, file_name: str):
    logger.info(f"Logging download for user {telegram_id} with torrent hash {torrent_hash} and file name {file_name}")

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Sorry, you are not authorized to use this bot.")
        return
    await message.reply("Welcome! Send me a file and I'll start printing it.")

@dp.message(F.document)
async def handle_torrent_file(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Sorry, you are not authorized to use this bot.")
        return

    document = message.document
    
    print_pages = message.caption or "all"
    print(f"printing pages: {print_pages}")

    if not document.file_name.endswith('.pdf'):
        await message.reply("Please send a .pdf file!")
        return

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file = await bot.get_file(document.file_id) # get file from telegram
        await bot.download_file(file.file_path, tmp_file.name) # download file from telegram to tmp file
        
        try: 
            job_id = print_file(tmp_file.name, printer_name=MINI_PRINTER, page=print_pages)
            await message.reply(f"I've sent your file to the printer! Job ID: {job_id}")
        except Exception as e:
            await message.reply(f"Error: {str(e)}")

# @dp.message(F.text.startswith('/status_'))
# async def check_status(message: types.Message):
#     if not await is_authorized(message.from_user.id):
#         await message.reply("Sorry, you are not authorized to use this bot.")
#         return

#     torrent_hash = message.text[8:]
    
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(f"{TORRENT_SERVER}/torrent/status/{torrent_hash}") as resp:
#                 if resp.status == 200:
#                     status = await resp.json()
#                     await message.reply(
#                         f"📥 Download Status:\n\n"
#                         f"Name: {status['name']}\n"
#                         f"Progress: {status['progress']:.2f}%\n"
#                         f"Speed: {status['download_rate']:.2f} KB/s\n"
#                         f"State: {status['state']}\n"
#                         f"Downloaded: {status['downloaded_size'] / (1024*1024):.2f} MB\n"
#                         f"Total Size: {status['total_size'] / (1024*1024):.2f} MB",
#                         parse_mode=ParseMode.HTML
#                     )
#                 else:
#                     await message.reply("Failed to get torrent status.")
#     except Exception as e:
#         await message.reply(f"Error: {str(e)}")

@dp.message(Command('help'))
async def send_help(message: types.Message):
    help_text =(
        "Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status_<hash> - Check torrent status\n"
        "/stop_<hash> - Stop torrent\n"
        # "/resume_<hash> - Resume stopped torrent\n"
        # "/delete_<hash> - Delete torrent (keeps files)\n"
        # "/deletewith_<hash> - Delete torrent with data"
    )

    await message.reply(help_text)

async def main():
    logger.info('Starting bot...')
    bot_info = await bot.get_me()
    logger.info(f'Bot started: {bot_info.username}')

    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)