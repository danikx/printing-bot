import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN= os.getenv('TELEGRAM_BOT_TOKEN', None)
USER_SPECIFIC_ID = int(os.getenv('USER_SPECIFIC_ID', -1))
MINI_PRINTER = os.getenv('MINI_PRINTER', 'Canon_LBP3010_LBP3018_LBP3050')
USERS = os.getenv('USER_SPECIFIC_ID=145091384', '')

def auth_user():
    return [int(user) for user in USERS.split(',') if user]