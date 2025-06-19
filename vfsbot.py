import os
import time
import requests
from telegram import Bot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import pytesseract
import io

# Настройки Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

# Список городов и кодов VFS
LOCATIONS = {
    "Москва": "moscow",
    "Санкт-Петербург": "saint-petersburg",
    "Екатеринбург": "ekaterinburg",
    "Казань": "kazan",
    "Новосибирск": "novosibirsk",
    "Нижний Новгород": "nizhniy-novgorod",
    "Самара": "samara",
    "Ростов-на-Дону": "rostov-on-don",
    "Краснодар": "krasnodar"
}

# Храним уникальные слоты, чтобы не дублировать сообщения
SENT_ALERTS = set()

SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 300))
VFS_BASE_URL = os.getenv("VFS_BASE_URL", "https://visa.vfsglobal.com/rus/ru/fra/book-an-appointment")


def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")


def check_slot(location, center):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        url = f"https://visa.vfsglobal.com/rus/ru/fra/book-an-appointment"
        driver.get(url)

        wait = WebDriverWait(driver, 20)

        location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "location-dropdown")))
        location_dropdown.click()
        time.sleep(1)
        location_option = driver.find_element(By.XPATH, f"//li[contains(text(), '{location}')]")
        location_option.click()

        center_dropdown = wait.until(EC.presence_of_element_located((By.ID, "center-dropdown")))
        center_dropdown.click()
        time.sleep(1)
        center_option = driver.find_element(By.XPATH, f"//li[contains(text(), '{center}')]")
        center_option.click()

        continue_button = wait.until(EC.element_to_be_clickable((By.ID, "btnContinue")))
        continue_button.click()

        captcha_img = wait.until(EC.presence_of_element_located((By.ID, "captcha_image")))
        location_png = captcha_img.screenshot_as_png
        image = Image.open(io.BytesIO(location_png))
        captcha_text = pytesseract.image_to_string(image).strip()

        captcha_input = driver.find_element(By.ID, "CaptchaInputText")
        captcha_input.send_keys(captcha_text)

        submit = driver.find_element(By.ID, "CaptchaButton")
        submit.click()

        time.sleep(5)
        if "no-appointments" not in driver.page_source.lower():
            return True
        return False

    except Exception as e:
        print(f"Ошибка в {location}: {e}")
        return False

    finally:
        driver.quit()


while True:
    for city_name, city_code in LOCATIONS.items():
        print(f"\n🔍 Проверка слотов: {city_name}")
        slot_available = check_slot(city_name, "TLS")
        if slot_available:
            if city_name not in SENT_ALERTS:
                message = f"✅ Найден слот для Французской визы:\n📍 Город: {city_name}\n🔗 {VFS_BASE_URL}"
                send_alert(message)
                SENT_ALERTS.add(city_name)
        else:
            print(f"❌ Слотов нет: {city_name}")

    print(f"⏳ Ожидание {SLEEP_INTERVAL} секунд до следующего цикла...\n")
    time.sleep(SLEEP_INTERVAL)
