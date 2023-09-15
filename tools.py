import logging
import os
import re
import time
from typing import Optional, List

from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from smsactivate.api import SMSActivateAPI
from telethon import TelegramClient

from schemas import NumberGet, RegisterUserData
from settings import SMS_ACTIVATE_API_KEY, DEVICE_NAME, APPIUM_SERVER_URL, APP_API_ID, APP_API_HASH, APP_PACKAGE
from appium.webdriver.webelement import WebElement as MobileWebElement

sa = SMSActivateAPI(SMS_ACTIVATE_API_KEY)
sa.debug_mode = True

COUNTRY_CODES = {
    "16": "44",  # UK
    # "6": "62", INDONESIA
    # "12": "1",  # USA
    # "187": "1",  # USA
    # "36": "1",  # Canada
    "0": "7"  # Russia
}

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_wd(no_reset=True):
    options = AppiumOptions()
    options.load_capabilities({
        "appium:deviceName": DEVICE_NAME,
        "appium:platformName": "android",
        "appium:appPackage": APP_PACKAGE,
        "appium:appActivity": "org.telegram.messenger.DefaultIcon",
        "appium:automationName": 'uiautomator2',
        "appium:noReset": no_reset,
        "appium:autoGrantPermissions": True,
        "appium:newCommandTimeout": 0,
    })
    return webdriver.Remote(APPIUM_SERVER_URL, options=options)


def find_elements(wd: webdriver.Remote, xpath: str, max_retries=2, sleep_time=2) -> Optional[List[MobileWebElement]]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.XPATH, xpath)
        if elements:
            return elements
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)


def find_element(wd: webdriver.Remote, xpath: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.XPATH, xpath)
        if elements:
            return elements[0]
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)


def find_by_id(wd: webdriver.Remote, _id: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.ID, _id)
        if elements:
            return elements[0]
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)


def find_by_text(wd: webdriver.Remote, text: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        try:
            messages = wd.find_elements(AppiumBy.CLASS_NAME, 'android.widget.TextView')

            for msg in messages:
                if text.lower() in msg.text.lower():
                    return msg
            if retries == max_retries:
                return None
            retries += 1
            time.sleep(sleep_time)
        except Exception as e:
            logger.error(e)
            time.sleep(sleep_time)
            continue


def register_number(wd: webdriver.Remote, number: NumberGet, register_user_data: RegisterUserData) -> Optional[
    NumberGet]:
    """Регистрирует номер, затем либо возвращает None если номер забанен или с паролем"""
    # Сначала обрабатываем всевозможные сценарии когда окно не в правильном состоянии
    start_messaging_btn = find_by_text(wd, "Start Messaging")
    if start_messaging_btn:
        logger.info("Start messaging button found, click...")
        start_messaging_btn.click()
    else:
        logger.info("Start messaging button not found...")

    country_code_input = find_element(wd, '//android.widget.EditText[@content-desc="Country code"]')
    if country_code_input:
        country_code_input.clear().send_keys(number.country_code)  # country code

    time.sleep(5)
    phone_number = find_element(wd, '//android.widget.EditText[@content-desc="Phone number"]')

    if phone_number:
        phone_number.clear()  # Phone number (without country code)
        phone_number.send_keys(number.phone_number)

    banned_number = find_by_text(wd, "This phone number is banned.")
    if banned_number:
        logger.error("Phone number is banned")
        return None

    # Если Password - то док-ва
    logger.info("Screenshot screen_before.png...")
    wd.save_screenshot(f"screen_before_{number.full_phone_number}.png")

    next_btn = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View')  # Next button
    if next_btn:
        next_btn.click()
    else:
        return None

    is_this_correct = find_by_text(wd, 'Is this the correct number?')
    if is_this_correct:
        find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]').click()

    # На этом моменте может показаться сообщение о бане номера
    digit_input = find_element(wd, '//android.widget.EditText')
    if digit_input:
        # Если все норм вводим код
        retries = 0
        while True:
            sms = get_sms(number.activation_id)
            if sms:
                for index, digit in enumerate(sms):
                    find_element(wd, f'//android.widget.EditText[{index + 1}]').send_keys(digit)
                break
            time.sleep(5)
            if retries == 12:
                logger.info("Мы ждали минуту, но смс не пришло")
                return None
            retries += 1

        your_password_label = find_by_text(wd, "Your password")
        if your_password_label:
            logger.info("Number has a password, screen saved...")
            wd.save_screenshot(f"screen_after_{number.full_phone_number}.png")
            return None
        else:
            # Если все хорошо
            os.remove(f"screen_before_{number.full_phone_number}.png")

            first_name_input = find_element(wd, "//android.widget.EditText")
            if first_name_input:
                first_name_input.send_keys(register_user_data.first_name)
                ok_btn = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]')
                ok_btn.click()

            tos_label = find_by_text(wd, "Terms of Service")
            if tos_label:
                tos_accept_btn = find_element(wd,
                                              "/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.TextView[2]")
                tos_accept_btn.click()
            return number
    else:
        # обрабатываем только бан
        banned_ok_btn = find_element(wd,
                                     '/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.TextView[2]')
        if banned_ok_btn:
            logger.info("Ban")
            banned_ok_btn.click()

        internal_error_btn = find_by_text(wd, 'An internal error occurred. Please try again later.')
        if internal_error_btn:
            logger.info("Internal Error")
            ok_btn = find_element(wd,
                                  '/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.TextView')
            ok_btn.click()

        unable_to_send_sms = find_by_text(wd, 'Unable to send SMS. Please try again later.')
        if unable_to_send_sms:
            logger.info("Unable to Send SMS")
            find_element(wd, "/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget"
                             ".FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout["
                             "2]/android.widget.TextView").click()

        os.remove(f"screen_before_{number.full_phone_number}.png")

        return None


def get_code(wd: webdriver.Remote):
    """Состояние окна должно быть в дефолтном состоянии чата"""
    telegram_btn = find_element(wd, "//android.view.ViewGroup")
    telegram_btn.click()

    time.sleep(2)
    code_el = find_elements(wd, "//android.view.ViewGroup")[-1]
    code = re.findall("\d+", code_el.text)[0]
    logger.info(f"Code is: {code}")
    return code


async def save_number(wd: webdriver.Remote, number: NumberGet):
    client = TelegramClient(str(number.full_phone_number), APP_API_ID, APP_API_HASH)

    await client.start(phone=lambda: number.full_phone_number, code_callback=lambda: get_code(wd))
    me = await client.get_me()
    logger.info(f"Client {me.first_name} is saved at {number.full_phone_number}.session")


def get_number(service="tg", countries=tuple(COUNTRY_CODES.keys()), max_price: int = 35) -> Optional[NumberGet]:
    """Returns tg number"""
    for country in countries:
        r = sa.getNumberV2(service, country=country, maxPrice=max_price)
        if r.get('activationId'):
            country_code = COUNTRY_CODES[r.get('countryCode')]
            return NumberGet(activation_id=r.get('activationId'), full_phone_number=r.get('phoneNumber'),
                             phone_number=r.get('phoneNumber').removeprefix(country_code), country_code=country_code)


def get_sms(activation_id) -> Optional[str]:
    """Returns code or None"""
    r: str = sa.getStatus(activation_id)
    if r.startswith("STATUS_OK"):
        _, code = r.split(":")
        return code
