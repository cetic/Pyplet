from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

options = Options()
options.binary_location = "/usr/bin/chromium-browser"

options.add_argument("--no-sandbox")

options.add_argument("--headless=new")
service = Service("/usr/lib/chromium-browser/chromedriver")

driver = webdriver.Chrome(service=service, options=options)

driver.get("http://127.0.0.1:8080/apps/template/template")
time.sleep(3)

container = driver.find_element(By.ID, "container")
input_field = container.find_element(By.TAG_NAME, "input")

input_field.send_keys("Hello from Selenium !")
input_field.send_keys(Keys.ENTER)

time.sleep(3)

messages = container.find_elements(By.TAG_NAME, "p")
message_got_sent = False

for p in messages:
    print(p.text)
    if "Hello from Selenium !" in p.text:
        message_got_sent = True

if message_got_sent:
    print("Test successful !")
