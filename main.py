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
from selenium.webdriver.firefox.options import Options
import json


class InvalidJsonConfigFileException(Exception):
    def __init__(self, msg):
        super(InvalidJsonConfigFileException, self).__init__()
        print(f'Invalid JSON config file. "{msg}" not found.')


class GolestanGradeCheckerConfig:
    def __init__(self):
        self.os = 'OSx' if platform.system() == 'Darwin' else 'Linux'
        self.term, self.tg_notif, self.login_url = self._read_config()
        self.username, self.password, self.tg_token, self.tg_chat_id = self._read_env_config()

    # noinspection PyMethodMayBeStatic
    def _read_env_config(self):
        # dotenv is used to handle username and password security.
        load_dotenv(verbose=False)
        env_path = Path('./env') / '.env'
        load_dotenv(dotenv_path=str(env_path))

        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")
        tg_token = os.getenv("TOKEN")
        tg_chat_id = os.getenv("CHAT_ID")
        return username, password, tg_token, tg_chat_id

    # noinspection PyMethodMayBeStatic
    def _read_config(self):
        with open('config.json') as f:
            data = json.load(f)

        if 'term_no' not in data:
            raise InvalidJsonConfigFileException('term_no')
        if 'tele_notif' not in data:
            raise InvalidJsonConfigFileException('tele_notif')
        if 'golestan_login_url' not in data:
            raise InvalidJsonConfigFileException('golestan_login_url')

        return data['term_no'], data['tele_notif'], data['golestan_login_url']


class GolestanGradeChecker:
    def __init__(self):
        self.config = GolestanGradeCheckerConfig()
        self.driver = self._setup_driver()
        self.updater = Updater(self.config.tg_token) if self.config.tg_notif else None
        self._start()

    # noinspection PyMethodMayBeStatic
    def _setup_driver(self):
        # setup Firefox profile (you can use other browsers, but I prefer Firefox)
        options = Options()
        options.add_argument('-headless')  # run in headless mode (without gui)
        fp = webdriver.FirefoxProfile()
        fp.set_preference("browser.tabs.remote.autostart", False)
        fp.set_preference("browser.tabs.remote.autostart.1", False)
        fp.set_preference("browser.tabs.remote.autostart.2", False)
        driver = webdriver.Firefox(fp, options=options)
        return driver

    def _start(self):
        if self.config.os is 'OSx':
            self._mac_notify("Golestan", 'By Ali_Tou', 'Golestan Grade Checker is running', sound_on=False)
        else:
            s.call(['notify-send', 'Golestan Grade Checker is running', 'By Ali_Tou'])

    def run(self):
        self._login_to_golestan()
        sleep(20)
        self._go_to_etelaate_jame_daneshjoo_page()
        sleep(7)
        self._go_to_semester()
        sleep(7)

        self.driver.switch_to.default_content()
        self._switch_to_grades_frame(3)
        sleep(0.5)
        self.loop()

    def loop(self):
        previous_grades = None  # it will be changed to dictionary later
        while True:
            given_grades = self._find_given_grades()
            if previous_grades is not None and previous_grades != given_grades:
                diff = list(set(given_grades.items()) ^ set(previous_grades.items()))
                new_grades_message = self._create_grades_message(diff)

                # Print on console
                print('You have new grades!')
                print(new_grades_message)
                print('---------')

                self._send_notification(new_grades_message)

            previous_grades = given_grades

            # give professors some time to insert our grades -_-
            sleep(180)

            self._refresh_grades_page()

    def _switch_to_grades_frame(self, faci_id):
        """
        Golestan uses frames. To access main body of page, we need to switch between its frames
        This function switches driver to main frame of grades in Etelaate Jame-e Daneshjoo.
        :param faci_id: Golestan frames has a Faci_id which is the id of that frame.
                According to our usage, we need to navigate to different Faci_ids.
        """
        self._switch_to_main_frame(faci_id)
        frame = self.driver.find_element_by_xpath('/html/body')
        frame = frame.find_element_by_xpath(""".//iframe[@id="FrameNewForm"]""")
        self.driver.switch_to.frame(frame)

    def _switch_to_main_frame(self, faci_id):
        """
        Golestan uses frames. To access main body of page, we need to switch between its frames
        This function switches driver to main frame of page (the contents)
        :param faci_id: Golestan frames has a Faci_id which is the id of that frame.
                According to our usage, we need to navigate to different Faci_ids.
        """
        WebDriverWait(self.driver, 50) \
            .until(ec.frame_to_be_available_and_switch_to_it((By.XPATH, f"""//*[@id="Faci{faci_id}"]""")))
        frame = self.driver.find_element_by_xpath('/html/frameset/frameset/frame[2]')
        self.driver.switch_to.frame(frame)
        frame = self.driver.find_element_by_xpath('/html/frameset/frame[3]')
        self.driver.switch_to.frame(frame)

    def _login_to_golestan(self):
        """
        Logs into Golestan system.
        You may need to change xpath of username and password fields if according to your university login web page.
        """
        self.driver.get(self.config.login_url)
        username_field = self.driver.find_element_by_xpath("""//input[@id="usename-field"]""")
        password_field = self.driver.find_element_by_xpath("""//input[@id="password"]""")
        username_field.send_keys(self.config.username)
        password_field.send_keys(self.config.password)
        password_field.send_keys(Keys.ENTER)

    def _go_to_etelaate_jame_daneshjoo_page(self):
        """
        From golestan main page, it navigates to Etelaate Jame-e Daneshjoo page
        """
        self._switch_to_main_frame(2)
        sleep(5)
        etelaate_jame_daneshjoo_button = self.driver.find_element_by_xpath("""//*[text()='اطلاعات جامع دانشجو']""")
        etelaate_jame_daneshjoo_button.click()
        sleep(1)
        etelaate_jame_daneshjoo_button.click()

    def _go_to_semester(self):
        """
        From Etelaate Jame-e Daneshjoo, it navigates to your dedicated term page
        """
        self.driver.switch_to.default_content()
        self._switch_to_main_frame(3)

        terms_status_table = self.driver.find_element_by_xpath("""//table[@id="T01"]""")
        term_field = terms_status_table.find_element_by_xpath(
            f"""//tr[@class="TableDataRow"][{self.config.term}]/td[1]""")
        term_field.click()

    def _find_given_grades(self):
        """
        When driver is in the page of a semester, this function finds number of courses which has grades
        :return: number of courses with given grades
        """
        result = {}
        grades_table = self.driver.find_element_by_xpath(""".//table[@id="T02"]""")
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

    def _refresh_grades_page(self):
        """
        This is dummy!
        Preventing Golestan to log us out because of inactivity, by clicking on previous term and next term.
        NOTE: This doesn't work when you're a freshman (When you don'y have any previous term)
            (Subject to change if another solution is found)
        """
        previous_term = self.driver.find_element_by_xpath(""".//img[@title="ترم قبلي"]""")
        previous_term.click()
        sleep(5)
        self.driver.switch_to.default_content()
        self._switch_to_grades_frame(3)
        next_term = self.driver.find_element_by_xpath(""".//img[@title="ترم بعدي"]""")
        next_term.click()
        sleep(5)

    # noinspection PyMethodMayBeStatic
    def _create_grades_message(self, grades):
        """
        Takes a list of tuples of grades in format (NAME, GRADE) and returns a beautified string
        :param grades: a list of tuples of grades
        :return: beautified string of grades with names and marks
        """
        return ", ".join([f"{name}: {mark}" for (name, mark) in grades])

    # noinspection PyMethodMayBeStatic
    def _mac_notify(self, title, subtitle, message, sound_on):
        title = '-title {!r}'.format(title)
        sub = '-subtitle {!r}'.format(subtitle)
        msg = '-message {!r}'.format(message)
        sound = '-sound default' if sound_on else ''
        os.system('terminal-notifier {}'.format(' '.join([msg, title, sub, sound])))

    def _send_notification(self, new_grades_message):
        if self.config.os == 'Osx':
            self._mac_notify("Golestan", 'Golestan Grade Checker',
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

        if self.config.tg_notif:
            self.updater.bot.send_message(chat_id=self.config.tg_chat_id,
                                          text=f"You have new grades in golestan!\nGiven Grades are"
                                          f" {new_grades_message}")


if __name__ == '__main__':
    ggc = GolestanGradeChecker()

    if ggc.config.tg_notif:
        from telegram.ext import Updater

    ggc.run()
