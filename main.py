#!/usr/bin/python3

import os
import platform
import subprocess as s
from time import sleep
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

OS = 'OSx' if platform.system() == 'Darwin' else 'Linux'
TERM_NO = 5  # Which term are you in?
TELEGRAM_NOTIF = False

if TELEGRAM_NOTIF:
    from telegram.ext import Updater

# University of Tehran CAS Url (Change to yours, if you are not a UT student)
UTCAS_URL = "https://auth4.ut.ac.ir:8443/cas/login?service=https://ems1.ut.ac.ir/forms/casauthenticateuser/\
casmu.aspx?ut=1%26CSURL=https://auth4.ut.ac.ir:8443/cas/logout?service$https://ems.ut.ac.ir/"


def mac_notify(title, subtitle, message, sound_on):
    title = '-title {!r}'.format(title)
    sub = '-subtitle {!r}'.format(subtitle)
    msg = '-message {!r}'.format(message)
    sound = '-sound default' if sound_on else ''
    os.system('terminal-notifier {}'.format(' '.join([msg, title, sub, sound])))


if OS is 'OSx':
    mac_notify("Golestan", 'By Ali_Tou', 'Golestan Grade Checker is running', sound_on=False)
else:
    s.call(['notify-send', 'Golestan Grade Checker is running', 'By Ali_Tou'])


# dotenv is used to handle username and password security.
load_dotenv(verbose=False)
env_path = Path('./env') / '.env'
load_dotenv(dotenv_path=str(env_path))

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# setup Firefox profile (you can use other browsers, but I prefer Firefox)
fp = webdriver.FirefoxProfile()
fp.set_preference("browser.tabs.remote.autostart", False)
fp.set_preference("browser.tabs.remote.autostart.1", False)
fp.set_preference("browser.tabs.remote.autostart.2", False)

driver = webdriver.Firefox(fp)

updater = None
if TELEGRAM_NOTIF:
    updater = Updater(TOKEN)


def switch_to_grades_frame(faci_id):
    """
    Golestan uses frames. To access main body of page, we need to switch between its frames
    This function switches driver to main frame of grades in Etelaate Jame-e Daneshjoo.
    :param faci_id: Golestan frames has a Faci_id which is the id of that frame.
            According to our usage, we need to navigate to different Faci_ids.
    """
    switch_to_main_frame(faci_id)
    frame = driver.find_element_by_xpath('/html/body')
    frame = frame.find_element_by_xpath(""".//iframe[@id="FrameNewForm"]""")
    driver.switch_to.frame(frame)


def switch_to_main_frame(faci_id):
    """
    Golestan uses frames. To access main body of page, we need to switch between its frames
    This function switches driver to main frame of page (the contents)
    :param faci_id: Golestan frames has a Faci_id which is the id of that frame.
            According to our usage, we need to navigate to different Faci_ids.
    """
    WebDriverWait(driver, 50)\
        .until(ec.frame_to_be_available_and_switch_to_it((By.XPATH, f"""//*[@id="Faci{faci_id}"]""")))
    frame = driver.find_element_by_xpath('/html/frameset/frameset/frame[2]')
    driver.switch_to.frame(frame)
    frame = driver.find_element_by_xpath('/html/frameset/frame[3]')
    driver.switch_to.frame(frame)


def login_to_golestan(login_url, username, password):
    """
    Logs into Golestan system.
    You may need to change xpath of username and password fields if according to your university login web page.
    :param login_url: Main URL of logging into your Golestan system
    :param username: Your username to Golestan
    :param password: Your password to Golestan
    """
    driver.get(login_url)
    username_field = driver.find_element_by_xpath("""//input[@id="usename-field"]""")
    password_field = driver.find_element_by_xpath("""//input[@id="password"]""")
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.ENTER)


def go_to_etelaate_jame_daneshjoo_page():
    """
    From golestan main page, it navigates to Etelaate Jame-e Daneshjoo page
    """
    switch_to_main_frame(2)
    sleep(5)
    etelaate_jame_daneshjoo_button = driver.find_element_by_xpath("""//*[text()='اطلاعات جامع دانشجو']""")
    etelaate_jame_daneshjoo_button.click()
    sleep(1)
    etelaate_jame_daneshjoo_button.click()


def go_to_semester(term_no):
    """
    From Etelaate Jame-e Daneshjoo, it navigates to your dedicated term page
    :param term_no: Which term are you going to check your grades?
    """
    driver.switch_to.default_content()
    switch_to_main_frame(3)

    terms_status_table = driver.find_element_by_xpath("""//table[@id="T01"]""")
    term_field = terms_status_table.find_element_by_xpath(f"""//tr[@class="TableDataRow"][{term_no}]/td[1]""")
    term_field.click()


def find_given_grades():
    """
    When driver is in the page of a semester, this function finds number of courses which has grades
    :return: number of courses with given grades
    """
    result = {}
    grades_table = driver.find_element_by_xpath(""".//table[@id="T02"]""")
    grades_table = grades_table.find_element_by_xpath(""".//tbody""")
    grades_rows = grades_table.find_elements_by_xpath(""".//tr[@class="TableDataRow"]""")
    print("Currently given Grades are:")
    for row in grades_rows:
        course_name = row.find_element_by_xpath(""".//td[6]""").get_attribute("title")
        grade_element = row.find_element_by_xpath(""".//td[9]""")
        course_grade = grade_element.find_element_by_xpath(""".//nobr[1]""").text
        if course_grade != "":
            print(course_name, course_grade)
            result[course_name] = course_grade
    return result


def refresh_grades_page():
    """
    This is dummy!
    Preventing Golestan to log us out because of inactivity, by clicking on previous term and next term.
    NOTE: This doesn't work when you're a freshman (When you don'y have any previous term)
        (Subject to change if another solution is found)
    """
    previous_term = driver.find_element_by_xpath(""".//img[@title="ترم قبلي"]""")
    previous_term.click()
    sleep(5)
    driver.switch_to.default_content()
    switch_to_grades_frame(3)
    next_term = driver.find_element_by_xpath(""".//img[@title="ترم بعدي"]""")
    next_term.click()
    sleep(5)


def create_grades_message(grades):
    """
    Takes a list of tuples of grades in format (NAME, GRADE) and returns a beautified string
    :param grades: a list of tuples of grades
    :return: beautified string of grades with names and marks
    """
    result = ""
    for index, (name, mark) in enumerate(grades):
        result += f"{name}: {mark}"
        if index < len(grades) - 1:
            result += ", "
    return result


login_to_golestan(UTCAS_URL, USERNAME, PASSWORD)
sleep(20)
go_to_etelaate_jame_daneshjoo_page()
sleep(7)
go_to_semester(TERM_NO)
sleep(7)

driver.switch_to.default_content()
switch_to_grades_frame(3)
sleep(0.5)

previous_grades = -1  # it will be changed to dictionary later
while True:
    given_grades = find_given_grades()
    if previous_grades != -1 and previous_grades != given_grades:
        diff = list(set(given_grades.items()) ^ set(previous_grades.items()))
        new_grades_message = create_grades_message(diff)

        # Print on console
        print('You have new grades!')
        print(new_grades_message)
        print('---------')

        if OS is 'Osx':
            mac_notify("Golestan", 'Golestan Grade Checker',
                       f'You have new grades in golestan! {new_grades_message}', sound_on=True)
        else:
            # Play a beep sound (using sox)
            s.call(['play',
                    '--no-show-progress',
                    '--null',
                    '-t', 'alsa',
                    '--channels', '1',
                    'synth', '1',
                    'sine', '330'])

            # Send a desktop notification (using notify-send)
            s.call(['notify-send', 'Golestan Grade Checker',
                    f'You have new grades in golestan! {new_grades_message}'])

        if TELEGRAM_NOTIF:
            updater.bot.send_message(chat_id=CHAT_ID,
                                     text=f"You have new grades in golestan!\nGiven Grades are {new_grades_message}")

    previous_grades = given_grades

    # give professors some time to insert our grades -_-
    sleep(180)

    refresh_grades_page()
