import os

from dotenv import load_dotenv

load_dotenv()

SMS_ACTIVATE_API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")
DEVICE_NAME = os.getenv("DEVICE_NAME")
APPIUM_SERVER_URL = os.getenv('APPIUM_SERVER_URL')

APP_API_ID = os.getenv('APP_API_ID')
APP_API_HASH = os.getenv('APP_API_HASH')
APP_PACKAGE = "org.telegram.messenger.web"
