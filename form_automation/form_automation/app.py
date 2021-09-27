from datetime import date, timedelta
import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Constants
TODAY = (date.today() + timedelta(days=1)).strftime('%d/%m/%y') # On Saturday
TODAY_LIST = TODAY.split('/')
DAY = TODAY_LIST[0]
MONTH = TODAY_LIST[1]
YEAR = '20' + TODAY_LIST[2]

DATA = [
    ['ENTER_EMAIL_HERE'], # Email
    ['ENTER_NAME_HERE'], # Name
    ['ENTER_PHONE_NUMBER_HERE'] # Contact
]

MODE = os.environ['MODE']# DEV OR PROD
URL = os.environ['FORM_URL']
CAPTCHA_URL_1 = os.environ['CAPTCHA_URL_1']
API_KEY = os.environ['CAPTCHA_API_KEY'] # 2Captcha API

# Headless Browser Chrome Option
options = Options()
options.binary_location = '/opt/headless-chromium'
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--single-process')
options.add_argument('--disable-dev-shm-usage')

# Run driver in headless mode
driver = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
driver.get(URL)

def auto_fill_form(i):
    # Handle email input
    email_bar = driver.find_element_by_css_selector("input[type=email]")
    email_bar.clear()
    email_bar.send_keys(DATA[0][i])

    # Check all checkboxes
    checkboxes = driver.find_elements_by_css_selector('div .quantumWizTogglePapercheckboxEl')

    for checkbox in checkboxes:
        checkbox.click()

    # Handle date input
    input_bar = driver.find_element_by_css_selector("input[type=date]")
    input_bar.send_keys(MONTH + DAY + YEAR)

    # Handle name and contact phone number input
    input_text_bars = driver.find_elements_by_css_selector("input[type=text]")

    for j in range(len(input_text_bars)):
        input_text_bars[j].clear()
        input_text_bars[j].send_keys(DATA[j + 1][i])

    # Handle multi-select input
    multi_select_bar = driver.find_element_by_css_selector('div[aria-posinset="2"]')
    multi_select_bar.click()

    try:
        # Get attribute of site key
        site_key = driver.find_element_by_css_selector("#recaptcha").get_attribute('data-sitekey')

        # Send captcha details to 2Captcha
        form = {
            "method": "userrecaptcha",
            "googlekey": site_key,
            "key": API_KEY, 
            "pageurl": URL, 
            "json": 1
        }

        # Get first request from 2Captcha
        res = requests.post(CAPTCHA_URL_1, data=form)
        res_id = res.json()['request']

        # Get second request from 2Captcha to solve problem
        CAPTCHA_URL_2 = f'http://2captcha.com/res.php?key={API_KEY}&action=get&id={res_id}&json=1'
        status = 0

        while not status:
            res = requests.get(CAPTCHA_URL_2)
            if res.json()['status'] == 0:
                time.sleep(3)
            else:
                req_captcha = res.json()['request']
                js = f'document.getElementById("g-recaptcha-response").innerHTML="{req_captcha}"'
                driver.execute_script(js)
                status = 1
    except Exception as e:
        print(e)

    # Handle submit
    submit_button = driver.find_element_by_css_selector("div[role=button].freebirdFormviewerViewNavigationSubmitButton")
    if MODE == 'PROD':
        submit_button.click()
    
    try: 
        # attempt to refresh
        driver.get(URL)

        if MODE == "DEV":
            # wait until alert is present
            WebDriverWait(driver, 5).until(EC.alert_is_present())

            # switch to alert and accept it
            driver.switch_to.alert.accept()

    except TimeoutException:
        print("No alert was present.")

def lambda_handler(event, context):
    for i in range(len(DATA[0])):
        auto_fill_form(i)
    return 'SUCCESS'