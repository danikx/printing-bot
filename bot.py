import os
import aiohttp
import asyncpg
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import tempfile
from config import TELEGRAM_BOT_TOKEN, USER_SPECIFIC_ID, MINI_PRINTER, auth_user
import asyncio
import re 
import urllib.parse
import logging
import hashlib
from print_file import print_file, get_printer_queue
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

whitelisted_users = auth_user()

document_queue = {}

class PrintingStates(StatesGroup):
    waiting_for_pages = State()
    waiting_for_copies = State()
    confirming = State()

class PrintingCallback(CallbackData, prefix="print"):
    action: str
    value: str = None

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
async def handle_document(message: types.Message, state: FSMContext):
    if not await is_authorized(message.from_user.id):
        await message.reply("Sorry, you are not authorized to use this bot.")
        return

    document = message.document
    
    if not document.file_name.endswith(('.pdf', '.doc', '.docx')):
        await message.reply("Please send a PDF, DOC, or DOCX file!")
        return

    # Save document info in state
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, tmp_file.name)
        
        await state.update_data(
            file_path=tmp_file.name,
            file_name=document.file_name
        )

    # Ask for pages
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="All pages", callback_data=PrintingCallback(action="pages", value="all").pack()),
            InlineKeyboardButton(text="Select pages", callback_data=PrintingCallback(action="pages", value="select").pack())
        ]
    ])
    
    await message.reply(
        "Please choose pages to print:",
        reply_markup=keyboard
    )
    await state.set_state(PrintingStates.waiting_for_pages)

@dp.callback_query(PrintingCallback.filter(F.action == "pages"))
async def process_pages_choice(callback: types.CallbackQuery, callback_data: PrintingCallback, state: FSMContext):
    if callback_data.value == "all":
        await state.update_data(pages="all")
        await ask_for_copies(callback.message, state)
    else:
        await callback.message.edit_text(
            "Please enter page range (e.g., '1-3,5,7-9'):"
        )
    await callback.answer()

@dp.message(PrintingStates.waiting_for_pages)
async def process_pages_input(message: types.Message, state: FSMContext):
    pages = message.text.strip()
    
    # Validate page range format
    if not validate_page_range(pages):
        await message.reply("Invalid page range format. Please use format like '1-3,5,7-9'")
        return
    
    await state.update_data(pages=pages)
    await ask_for_copies(message, state)

async def ask_for_copies(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data=PrintingCallback(action="copies", value="1").pack()),
            InlineKeyboardButton(text="2", callback_data=PrintingCallback(action="copies", value="2").pack()),
            InlineKeyboardButton(text="3", callback_data=PrintingCallback(action="copies", value="3").pack())
        ],
        [
            InlineKeyboardButton(text="Other amount", callback_data=PrintingCallback(action="copies", value="other").pack())
        ]
    ])
    
    await message.edit_text("How many copies do you need?", reply_markup=keyboard)
    await state.set_state(PrintingStates.waiting_for_copies)

@dp.callback_query(PrintingCallback.filter(F.action == "copies"))
async def process_copies_choice(callback: types.CallbackQuery, callback_data: PrintingCallback, state: FSMContext):
    if callback_data.value == "other":
        await callback.message.edit_text("Please enter number of copies (1-99):")
    else:
        await state.update_data(copies=int(callback_data.value))
        await show_confirmation(callback.message, state)
    await callback.answer()

@dp.message(PrintingStates.waiting_for_copies)
async def process_copies_input(message: types.Message, state: FSMContext):
    try:
        copies = int(message.text)
        if 1 <= copies <= 99:
            await state.update_data(copies=copies)
            await show_confirmation(message, state)
        else:
            await message.reply("Please enter a number between 1 and 99")
    except ValueError:
        await message.reply("Please enter a valid number")

async def show_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    confirmation_text = (
        f"📄 File: {data['file_name']}\n"
        f"📑 Pages: {data['pages']}\n"
        f"🔄 Copies: {data['copies']}\n\n"
        f"Would you like to proceed with printing?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=PrintingCallback(action="confirm", value="yes").pack()),
            InlineKeyboardButton(text="❌ Cancel", callback_data=PrintingCallback(action="confirm", value="no").pack())
        ]
    ])
    
    await message.edit_text(confirmation_text, reply_markup=keyboard)
    await state.set_state(PrintingStates.confirming)

@dp.callback_query(PrintingCallback.filter(F.action == "confirm"))
async def process_confirmation(callback: types.CallbackQuery, callback_data: PrintingCallback, state: FSMContext):
    if callback_data.value == "yes":
        data = await state.get_data()
        try:
            job_id = print_file(
                data['file_path'],
                printer_name=MINI_PRINTER,
                pages=None if data['pages'] == "all" else data['pages'],
                copies=data['copies']
            )
            
            await callback.message.edit_text(f"✅ Print job sent successfully!\nJob ID: {job_id}")
            
            # Wait for 5 seconds before checking the printing status
            await asyncio.sleep(5)
            await callback.message.reply(f"Checking printing status for Job ID: {job_id}")
            queue = get_printer_queue(printer_name=MINI_PRINTER)
            
        except Exception as e:
            await callback.message.edit_text(f"❌ Error: {str(e)}")
    else:
        await callback.message.edit_text("Printing cancelled")
    
    # Cleanup
    data = await state.get_data()
    if 'file_path' in data:
        try:
            os.unlink(data['file_path'])
        except:
            pass
    await state.clear()
    await callback.answer()

def validate_page_range(pages: str) -> bool:
    try:
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                if start <= 0 or end <= 0 or start > end:
                    return False
            else:
                if int(part) <= 0:
                    return False
        return True
    except ValueError:
        return False

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