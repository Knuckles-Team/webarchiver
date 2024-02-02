#!/usr/bin/env python3
# coding: utf-8

import sys
import getopt
import time
import os
import math
import re
import piexif
import requests
import urllib.request
import shutil
from multiprocessing import Pool
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageChops
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
try:
    from webarchiver.version import __version__, __author__, __credits__
except ModuleNotFoundError:
    from version import __version__, __author__, __credits__

def chunks(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


class Webarchiver:
    def __init__(self):
        self.urls = []
        self.file_urls = []
        self.driver = None
        self.home = os.path.expanduser("~")
        self.save_path = os.path.join(self.home, "Downloads")
        self.chrome_options = webdriver.ChromeOptions()
        self.firefox_options = webdriver.FirefoxOptions()
        self.image_format = 'png'
        self.image_quality = 80
        self.hidden_scroll_bar = 'hidden'
        self.screenshot_success = False
        self.screenshot_success_alt = False
        self.zoom_level = 100
        self.dpi = 1.0
        self.max_scroll_height = 369369
        self.processes = 1
        self.url_filter = None
        self.url_count = 0
        self.executor = "Local"
        self.host = "None"
        self.browser = "Chrome"

    def launch_browser(self):
        if self.browser.lower() == "chrome" and self.executor.lower() == "local":
            # Pass the argument 1 to allow and 2 to block
            self.chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2
            })
            # Add Ublock Origin to Chrome
            parent_dir = os.path.abspath(os.path.dirname(__file__))
            lib_dir = os.path.join(parent_dir, 'lib')
            sys.path.append(lib_dir)
            adblock_path = f'{lib_dir}/uBlock-Origin_v1.27.0.crx'
            if os.path.isfile(adblock_path):
                print(f"uBlock Origin Found: {adblock_path}")
                self.chrome_options.add_extension(adblock_path)
            elif os.path.isfile(f'{os.curdir}/lib/uBlock-Origin_v1.27.0.crx'):
                adblock_path = f'{os.curdir}/lib/uBlock-Origin_v1.27.0.crx'
                print(f"uBlock Origin Found: {adblock_path}")
                self.chrome_options.add_extension(adblock_path)
            else:
                print(f"uBlock Origin was not found")
            self.chrome_options.add_argument('--disable-gpu')
            self.chrome_options.add_argument('--start-maximized')
            self.chrome_options.add_argument('--hide-scrollbars')
            self.chrome_options.add_argument('--disable-infobars')
            self.chrome_options.add_argument('--disable-notifications')
            self.chrome_options.add_argument('--disable-dev-shm-usage')
            self.chrome_options.add_argument('--dns-prefetch-disable')
            self.chrome_options.set_capability("browserName", "chrome")
            if self.dpi != 1:
                self.chrome_options.add_argument(f'--force-device-scale-factor={self.dpi}')
                self.chrome_options.add_argument(f'--high-dpi-support={self.dpi}')
            try:
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                                               options=self.chrome_options)
                # Hide the scrollbar
                scrollbar_js = 'document.documentElement.style.overflow = \"{}\"'.format(self.hidden_scroll_bar)
                self.driver.execute_script(scrollbar_js)
            except Exception as e:
                print("Could not open with Latest Chrome Version. PLEASE ENSURE YOU'RE NOT RUNNING WITH SUDO", e)
                exit()
        elif self.browser.lower() == "firefox" and self.executor.lower() == "local":
            self.firefox_options.headless = True
            self.driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=self.firefox_options)
            self.driver.set_window_position(0, 0)
            self.driver.maximize_window()
        elif self.browser.lower() == "chrome" and self.executor.lower() != "local":
            browser_name = "Webarchiver"
            # Add Ublock Origin to Chrome
            parent_dir = os.path.abspath(os.path.dirname(__file__))
            lib_dir = os.path.join(parent_dir, 'lib')
            sys.path.append(lib_dir)
            adblock_path = f'{lib_dir}/uBlock-Origin_v1.27.0.crx'
            if os.path.isfile(adblock_path):
                print(f"uBlock Origin Found: {adblock_path}")
                self.chrome_options.add_extension(adblock_path)
            elif os.path.isfile(f'{os.curdir}/lib/uBlock-Origin_v1.27.0.crx'):
                adblock_path = f'{os.curdir}/lib/uBlock-Origin_v1.27.0.crx'
                print(f"uBlock Origin Found: {adblock_path}")
                self.chrome_options.add_extension(adblock_path)
            else:
                print(f"uBlock Origin was not found")
            self.chrome_options.add_argument('--disable-gpu')
            self.chrome_options.add_argument('--start-maximized')
            self.chrome_options.add_argument('--hide-scrollbars')
            self.chrome_options.add_argument('--disable-infobars')
            self.chrome_options.add_argument('--disable-notifications')
            self.chrome_options.add_argument('--disable-dev-shm-usage')
            self.chrome_options.add_argument('--dns-prefetch-disable')
            self.chrome_options.add_argument('--log-level=3')
            self.chrome_options.set_capability("browserName", "chrome")
            self.chrome_options.set_capability("browserVersion", "latest")
            self.chrome_options.set_capability(f"{self.host}:options", {
                "enableVideo": False,
                "enableVNC": True,
                "name": browser_name,
                "setAcceptInsecureCerts": True,
                "acceptSslCerts": True,
            })
            self.driver = webdriver.Remote(
                command_executor=self.executor,
                options=self.chrome_options,
            )
            self.driver.maximize_window()
        elif self.browser.lower() == "firefox" and self.executor.lower() != "local":
            browser_name = "Webarchiver"
            self.firefox_options.add_argument('--disable-gpu')
            self.firefox_options.add_argument('--start-maximized')
            self.firefox_options.add_argument('--hide-scrollbars')
            self.firefox_options.add_argument('--disable-infobars')
            self.firefox_options.add_argument('--disable-notifications')
            self.firefox_options.add_argument('--disable-dev-shm-usage')
            self.firefox_options.add_argument('--dns-prefetch-disable')
            self.firefox_options.add_argument('--log-level=3')
            self.firefox_options.set_capability("browserName", "chrome")
            self.firefox_options.set_capability("browserVersion", "latest")
            self.firefox_options.set_capability(f"{self.host}:options", {
                "enableVideo": False,
                "enableVNC": True,
                "name": browser_name,
                "setAcceptInsecureCerts": True,
                "acceptSslCerts": True,
            })
            self.driver = webdriver.Remote(
                command_executor=self.executor,
                options=self.firefox_options,
            )
            self.driver.maximize_window()

    def open_file(self, file):
        webarchiver_urls = open(file, 'r')
        for url in webarchiver_urls:
            if str(url).strip() != "":
                self.append_link(str(url).strip())
                self.append_file_link(str(url).strip())

    def append_link(self, url):
        # print(f"URL Appended: {url}")
        self.urls.append(url)
        self.urls = list(dict.fromkeys(self.urls))

    def append_file_link(self, url):
        # print(f"FILE URL Appended: {url}")
        self.file_urls.append(url)
        self.file_urls = list(dict.fromkeys(self.file_urls))

    def set_file_links(self, urls):
        # print(f"FILE URL Appended: {url}")
        cleaned_urls = []
        for url in urls:
            if str(url).strip() != "":
                cleaned_urls.append(str(url).strip())

        self.file_urls = cleaned_urls
        self.file_urls = list(dict.fromkeys(self.file_urls))

    def set_image_format(self, image_format):
        self.image_format = image_format

    def get_links(self):
        return self.urls

    def reset_links(self):
        print("Links Reset")
        self.urls = []

    def set_executor(self, executor="Local"):
        self.host = "None"
        self.executor = executor
        if executor.lower() != "local":
            self.host = executor.split('|')[0]
            self.executor = executor.split('|')[1]

    def set_browser(self, browser="Chrome"):
        self.browser = browser

    def set_zoom_level(self, zoom_percentage=100):
        self.zoom_level = zoom_percentage

    def set_dpi_level(self, dpi=1):
        self.dpi = dpi

    def read_url(self, url, zoom_percentage):
        try:
            self.driver.get(url)
            self.driver.execute_script(f"document.body.style.zoom='{zoom_percentage}%'")
            self.driver.execute_script('return document.readyState;')
        except Exception as e:
            print(f"Could not access website: {e}")
        # Tries to Remove any alerts that may appear on the page
        try:
            WebDriverWait(self.driver, 4).until(ec.alert_is_present(), 'Timed out waiting for any notification alerts')
            alert = self.driver.switch_to.alert
            alert.accept()
            print("WebPage Alert Accepted!")
        except Exception as e:
            print(f"No WebPage Alert! {e}")
        time.sleep(1)
        # Tries to remove any persistent scrolling headers/fixed/sticky'd elements on the page
        print("Removing Fixed Elements Scrub 1")
        self.remove_fixed_elements(url)
        print("Removing Fixed Elements Scrub 2")
        self.remove_fixed_elements(url)

    def clean_url(self):
        for url_index in range(0, len(self.urls)):
            self.urls[url_index] = re.sub('^chrome:.*$', '', self.urls[url_index])
            self.urls[url_index] = re.sub('^chrome-native:.*$', '', self.urls[url_index])
            self.urls[url_index] = re.sub('^.*facebook.*$', '', self.urls[url_index])
            self.urls[url_index] = re.sub('m.youtube', 'www.youtube', self.urls[url_index])
            self.urls[url_index] = re.sub('mobile.twitter', 'twitter', self.urls[url_index])
            self.urls[url_index] = re.sub('//m\.', 'www.', self.urls[url_index])
            self.urls[url_index] = self.urls[url_index].rstrip(os.linesep)
        try:
            self.urls.remove('\n')
        except ValueError:
            print("No Newlines Found")
        try:
            self.urls.remove('')
        except ValueError:
            print("No Empty Strings Found")
        self.urls = list(dict.fromkeys(filter(None, self.urls)))

    def screenshot(self, url, zoom_percentage=100, filename=None, quality=None):
        self.read_url(url, zoom_percentage)
        print(f"Quality: {quality}")
        if filename:
            title = re.sub('[\\\\/:"*?<>|\']', '', filename)
            title = (title[:140]) if len(title) > 140 else title
            self.driver.save_screenshot(f'{self.save_path}/{title}.{self.image_format}')
        else:
            print(f"Driver Title: {self.driver.title}")
            print(f"URL, {url}")
            if self.driver.title:
                title = re.sub('[\\\\/:"*?<>|\']', '', self.driver.title)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
                self.driver.save_screenshot(f'{self.save_path}/{title}.{self.image_format}')
            else:
                title = re.sub('[\\\\/:"*?<>|.,\']', '', url)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
                self.driver.save_screenshot(f'{self.save_path}/{title}.{self.image_format}')

    def full_page_screenshot(self, url, zoom_percentage=100, filename=None, quality=None):
        self.read_url(url, zoom_percentage)
        if filename:
            title = re.sub('[\\\\/:"*?<>|.,\']', '', filename)
            title = (title[:140]) if len(title) > 140 else title
        else:
            if self.driver.title:
                title = re.sub('[\\\\/:"*?<>|.,\']', '', self.driver.title)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
            else:
                title = re.sub('[\\\\/:"*?<>.,|\']', '', url)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
        zeroth_ifd = {
            piexif.ImageIFD.Make: u"Webarchiver",
            piexif.ImageIFD.Software: u"Webarchiver",
            piexif.ImageIFD.ImageDescription: f"{url}".encode('utf-8'),
        }
        exif_ifd = {
            piexif.ExifIFD.DateTimeOriginal: u"Today",
            piexif.ExifIFD.UserComment: f"{url}".encode('utf-8'),
        }
        gps_ifd = {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            # piexif.GPSIFD.GPSAltitudeRef: 1,
            piexif.GPSIFD.GPSDateStamp: u"1999:99:99 99:99:99",
        }
        first_ifd = {
            piexif.ImageIFD.Make: u"Webarchiver",
            piexif.ImageIFD.Software: u"Webarchiver"
        }
        scroll_to_js = 'window.scrollTo(0, {});'
        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": first_ifd}  # , "thumbnail": thumbnail}
        exif_bytes = piexif.dump(exif_dict)
        # define necessary image properties
        image_options = dict()
        # This will add the URL of the webite to the description
        image_options['exif'] = exif_bytes
        image_options['format'] = self.image_format
        image_options['quality'] = quality
        # Changes the ratio of the screen of the device.
        device_pixel_ratio_js = 'return window.devicePixelRatio;'
        device_pixel_ratio = self.driver.execute_script(device_pixel_ratio_js)
        print(f"Pixel Ratio: {device_pixel_ratio}")
        inner_height_js = 'return window.innerHeight;'
        inner_height = self.driver.execute_script(inner_height_js)
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            print(f"Error reading scroll height. {e}")
        self.driver.execute_script("window.scrollTo(0, 0)")
        scroll_height_js = 'return document.body.scrollHeight;'
        scroll_height = self.driver.execute_script(scroll_height_js)
        if scroll_height <= 0:
            print("Getting alternative scroll height")
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self.driver.execute_script("window.scrollTo(0, 0)")
            scroll_height_js = 'return document.documentElement.scrollHeight;'
            scroll_height = self.driver.execute_script(scroll_height_js)
            print(
                f"Scroll Height read as 0, Reading scroll height with alternative method. New height: {scroll_height}")

        if scroll_height > self.max_scroll_height:
            print(f"Original scroll height: {scroll_height} Maximum: {self.max_scroll_height}")
            scroll_height = self.max_scroll_height
        y_offset_js = 'return window.pageYOffset;'
        initial_offset = self.driver.execute_script(y_offset_js)
        actual_page_size = math.ceil(scroll_height * device_pixel_ratio)
        # Screenshot all slices
        print("Making Screen Slices")
        slices = []
        slice_count = 0
        for offset in range(0, scroll_height + 1, inner_height):
            self.driver.execute_script(scroll_to_js.format(offset))
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            img = Image.open(BytesIO(self.driver.get_screenshot_as_png()))
            slices.append(img)
            percentage = '%.3f' % ((offset / scroll_height) * 100)
            slice_count = slice_count + 1
            screenshot_processed = '{0: <25}'.format(f"Screenshot Processed: {slice_count}")
            percentage_display = '{0: <20}'.format(f"Percentage: {percentage}%")
            total = '{0: <15}'.format(f"Total: {offset}/{scroll_height}")
            print(f"{screenshot_processed} | {percentage_display} | {total}")
        percentage = '%.3f' % 100
        screenshot_processed = '{0: <25}'.format(f"Screenshot Processed: {slice_count + 1}")
        percentage_display = '{0: <20}'.format(f"Percentage: {percentage}%")
        total = '{0: <15}'.format(f"Total: {scroll_height}/{scroll_height}")
        print(f"{screenshot_processed} | {percentage_display} | {total}")
        # Glue Slices together
        print("Glueing Slices")
        image_file = Image.new('RGB', (slices[0].size[0], actual_page_size))
        for i, img in enumerate(slices[:-1]):
            image_file.paste(img, (0, math.ceil(i * inner_height * device_pixel_ratio)))
        else:
            image_file.paste(slices[-1], (0, math.ceil((scroll_height - inner_height) * device_pixel_ratio)))
        try:
            image_file.save(f'{self.save_path}/{title}.{self.image_format}', **image_options)
            self.screenshot_success = True
        except Exception as e:
            print("Could not save image error: ", e)
            try:
                os.remove(f'{self.save_path}/{title}.{self.image_format}')
            except Exception as e:
                print(f"Could not remove file, does it exist? {e}")
            self.screenshot_success = False

        y_offset_js = 'return window.pageYOffset;'
        new_offset = self.driver.execute_script(y_offset_js)

        if initial_offset != new_offset:
            self.driver.execute_script(scroll_to_js.format(initial_offset))

        if not self.screenshot_success:
            self.full_page_screenshot_alternative(url=f'{url}', zoom_percentage=zoom_percentage, filename=f'{title}',
                                                  quality=quality)

    def full_page_screenshot_alternative(self, url, zoom_percentage=100, filename=None, **kwargs):
        zeroth_ifd = {
            piexif.ImageIFD.Make: u"GeniusBot",
            # piexif.ImageIFD.XResolution: (96, 1),
            # piexif.ImageIFD.YResolution: (96, 1),
            piexif.ImageIFD.Software: u"GeniusBot",
            piexif.ImageIFD.ImageDescription: f"{url}".encode('utf-8'),
        }
        exif_ifd = {
            piexif.ExifIFD.DateTimeOriginal: u"Today",
            piexif.ExifIFD.UserComment: f"{url}".encode('utf-8'),
            # piexif.ExifIFD.LensMake: u"LensMake",
            # piexif.ExifIFD.Sharpness: 65535,
            # piexif.ExifIFD.LensSpecification: ((1, 1), (1, 1), (1, 1), (1, 1)),
        }
        gps_ifd = {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            # piexif.GPSIFD.GPSAltitudeRef: 1,
            piexif.GPSIFD.GPSDateStamp: u"1999:99:99 99:99:99",
        }
        first_ifd = {
            piexif.ImageIFD.Make: u"GeniusBot",
            # piexif.ImageIFD.XResolution: (40, 1),
            # piexif.ImageIFD.YResolution: (40, 1),
            piexif.ImageIFD.Software: u"GeniusBot"
        }
        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": first_ifd}  # , "thumbnail": thumbnail}
        exif_bytes = piexif.dump(exif_dict)
        # define necessary image properties
        image_options = dict()
        # This will add the URL of the webite to the description
        image_options['exif'] = exif_bytes
        image_options['format'] = kwargs.get('format') or self.image_format
        image_options['quality'] = kwargs.get('quality') or self.image_quality
        quality = kwargs.get('quality') or self.image_quality
        print("Attempting alternative screenshot method")
        self.driver.execute_script(f"window.scrollTo({0}, {0})")
        total_width = self.driver.execute_script("return document.body.offsetWidth")
        total_height = self.driver.execute_script("return document.body.parentNode.scrollHeight")
        viewport_width = self.driver.execute_script("return document.body.clientWidth")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        rectangles = []
        i = 0
        while i < total_height:
            ii = 0
            top_height = i + viewport_height
            if top_height > total_height:
                top_height = total_height
            while ii < total_width:
                top_width = ii + viewport_width
                if top_width > total_width:
                    top_width = total_width
                rectangles.append((ii, i, top_width, top_height))
                ii = ii + viewport_width
            i = i + viewport_height
        stitched_image = Image.new('RGB', (total_width, total_height))
        previous = None
        part = 0

        for rectangle in rectangles:
            if previous is not None:
                self.driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            file_name = "part_{0}.png".format(part)
            self.driver.get_screenshot_as_file(file_name)
            screenshot = Image.open(file_name)

            if rectangle[1] + viewport_height > total_height:
                offset = (rectangle[0], total_height - viewport_height)
            else:
                offset = (rectangle[0], rectangle[1])
            stitched_image.paste(screenshot, offset)
            del screenshot
            os.remove(file_name)
            part = part + 1
            previous = rectangle
        print(f"Saving image to: {self.save_path}/{filename}.{self.image_format}'")
        try:
            stitched_image.save(f"{self.save_path}/{filename}.{self.image_format}", **image_options)
            self.screenshot_success_alt = True
        except Exception as e:
            print("Could not save image error in alternative form: ", e)
            try:
                os.remove(f'{self.save_path}/{filename}.{self.image_format}')
            except Exception as e:
                print(f"Could not remove file, does it exist? {e}")
            self.screenshot_success_alt = False

        print("Finishing chrome full page screenshot workaround...")
        if not ImageChops.invert(
                stitched_image).getbbox() or not stitched_image.getbbox() or self.screenshot_success_alt is False:
            print("Could not save full page screenshot, saving single page screenshot instead")
            self.screenshot(url=f'{url}', zoom_percentage=zoom_percentage, filename=filename, quality=quality)

    def set_save_path(self, save_path):
        self.save_path = save_path
        self.save_path = self.save_path.replace(os.sep, '/')
        # print(f"Save Path: {self.save_path }")
        if save_path is None or save_path == "":
            self.save_path = f"{os.path.expanduser('~')}".replace("\\", "/")
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def remove_fixed_elements(self, url):
        try:
            self.driver.execute_script("window.scrollTo(0, 0)")
        except Exception as e:
            print(f"Unable to remove fixed elements {e}")

        try:
            # Try to scroll to bottom of page.
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            print("Unable to remove fixed elements")
            print(e)
            self.driver.get(url)
            self.driver.execute_script('return document.readyState;')

        print("Clicking Escape to clear popups")
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.driver.execute_script("window.scrollTo(0, 0)")
        scroll_to_js = 'window.scrollTo(0, {});'
        scroll_height_js = 'return document.body.scrollHeight;'
        scroll_height = self.driver.execute_script(scroll_height_js)
        if scroll_height > self.max_scroll_height:
            print(f"Original scroll height: {scroll_height} Maximum: {self.max_scroll_height}")
            scroll_height = self.max_scroll_height
        elif scroll_height == 0:
            scroll_height = 1080
        inner_height_js = 'return window.innerHeight;'
        inner_height = self.driver.execute_script(inner_height_js)
        for offset in range(0, scroll_height + 1, inner_height):
            self.driver.execute_script(scroll_to_js.format(offset))
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

            # Convert overflow to scroll and position to relative.
            try:
                # Removes Any Scroll bars
                self.driver.execute_script("""
                (function () {
                  for (let e of document.getElementsByClassName("Scroll--locked")) { 
                      e.style.overflow = "hidden"; 
                      e.style.position = "relative"; 
                  }                  
                  document.querySelector('html').style.overflow = 'hidden';
                  document.querySelector('html').style.position = 'relative';
                })();""")
            except Exception as e:
                print(e)
            print("Changed elements from to overflow scroll")

            # Removes Any Fixed Elements from body at top of page
            try:
                self.driver.execute_script("""
                (function () { 
                  var i, elements = document.querySelectorAll('body *');

                  for (i = 0; i < elements.length; i++) {
                    if (getComputedStyle(elements[i]).position === 'fixed' || getComputedStyle(elements[i]).position === 'sticky' || getComputedStyle(elements[i]).position === '-webkit-sticky') {
                      elements[i].parentNode.removeChild(elements[i]);
                    }
                  }
                })();""")
            except Exception as e:
                print(e)
            print("Removed elements from body")

            # Removes Any Fixed Elements from any div at top of page
            try:
                self.driver.execute_script("""
                (function () {
                  var i, elements = document.querySelectorAll('div *');

                  for (i = 0; i < elements.length; i++) {
                    if (getComputedStyle(elements[i]).position === 'fixed' || getComputedStyle(elements[i]).position === 'sticky' || getComputedStyle(elements[i]).position === '-webkit-sticky') {
                      elements[i].parentNode.removeChild(elements[i]);
                    }
                  }
                })();""")
            except Exception as e:
                print(e)
            print("Removed elements from all divs")
            try:
                # Removes Any Fixed Elements from any html main at top of page
                self.driver.execute_script("""
                (function () {
                  var i, elements = document.querySelectorAll('html *');
  
                  for (i = 0; i < elements.length; i++) {
                    if (getComputedStyle(elements[i]).position === 'fixed' || getComputedStyle(elements[i]).position === 'sticky' || getComputedStyle(elements[i]).position === '-webkit-sticky') {
                      elements[i].parentNode.removeChild(elements[i]);
                    }
                  }
                })();""")
            except Exception as e:
                print(e)
            print("Removed elements from html")

            percentage = '%.3f' % ((offset / scroll_height) * 100)
            prcessing_percentage = '{0: <48}'.format(f"Web Elements Processed Percentage: {percentage}%")
            total = '{0: <15}'.format(f"Total: {offset}/{scroll_height}")
            print(f"{prcessing_percentage} | {total}")
            print(f"{prcessing_percentage} | {total}")
        percentage = '%.3f' % 100
        prcessing_percentage = '{0: <48}'.format(f"Web Elements Processed Percentage: {percentage}%")
        total = '{0: <15}'.format(f"Total: {scroll_height}/{scroll_height}")
        print(f"{prcessing_percentage} | {total}")
        self.driver.execute_script("window.scrollTo(0, 0)")

    def enable_scroll(self):
        print("Attempting to re-enable scroll bar")
        body = self.driver.find_element(By.XPATH, '/html/body')
        self.driver.execute_script("arguments[0].setAttribute('style', 'overflow: scroll; overflow-x: scroll')", body)
        html = self.driver.find_element(By.XPATH, '/html')
        self.driver.execute_script("arguments[0].setAttribute('style', 'overflow: scroll; overflow-x: scroll')", html)
        print("Set scrolls override")

    def quit_driver(self):
        print("Chrome Driver Closed")
        self.driver.quit()

    def set_processes(self, processes):
        try:
            processes = int(processes)
            if processes > 0 or processes < os.cpu_count():
                self.processes = processes
            else:
                print(f"Did not recognize {processes} as a valid value, defaulting to CPU Count: {os.cpu_count()}")
                self.processes = os.cpu_count()
        except Exception as e:
            print(
                f"Did not recognize {processes} as a valid value, defaulting to CPU Count: {os.cpu_count()}\nError: {e}")
            self.processes = os.cpu_count()

    def set_url_filter(self, url_filter):
        self.url_filter = url_filter

    def scrape_urls_in_parallel(self):
        print("Scraping for URL(s)")
        scrape_pool = Pool(processes=self.processes)
        print("Pooling...")
        results = scrape_pool.map(self.scrape_urls, self.file_urls)
        print(f"Obtaining Results: {results}")
        for result in results:
            self.append_file_link(url=result)
        print(f"Found {len(self.file_urls)} file(s)")

    def scrape_urls(self, url):
        # Check if the url supplied is already a file of type below.
        print("Checking URL...")
        for url_filter in self.url_filter:
            if url_filter in str(url):
                print(f"URL Contains Content: {url}")
                return url
        print("Checking URL for Additional Content...")
        url = url.strip()
        reqs = requests.get(url)
        soup = BeautifulSoup(reqs.text, 'html.parser')
        file_link = []
        links = soup.find_all('a')
        for link in links:
            if link.get('href'):
                artifact_link = link.get('href').rstrip('/')
            else:
                continue
            if self.url_filter:
                if self.url_filter in url:
                    print(f"\tAdding ({len(file_link)}-{len(self.file_urls)}): {url}/{artifact_link}")
                    file_link.append(f"{url}/{artifact_link}")
                else:
                    print(f"\tSkipping: {url}/{artifact_link}")
            else:
                print(f"\tAdding ({len(file_link)}-{len(self.file_urls)}): {url}/{artifact_link}")
                file_link.append(f"{url}/{artifact_link}")
        return file_link

    def download_urls_in_parallel(self):
        print(f"Downloading {len(self.file_urls)} URL(s)\n{self.file_urls}")
        download_pool = Pool(processes=self.processes)
        download_pool.map(self.download_urls, self.file_urls)
        print("Cleaning empty directories")
        folders = list(os.walk(self.save_path))[1:]
        for folder in folders:
            if not folder[2]:
                os.rmdir(folder[0])

    def clean_file_name(self, file_name):
        file_name_filters = {
            "%20": " ",
            "%21": "!",
            "%22": '"',
            "%23": "#",
            "%24": "$",
            "%25": "%",
            "%26": "&",
            "%27": "'",
            "%28": "(",
            "%29": ")",
            "%2A": "*",
            "%2B": "+",
            "%2C": ",",
            "%2D": "-",
            "%2E": ".",
            "%2F": "_",
            "%3A": "_",
            "%3B": "_",
            "%3C": "_",
            "%3D": "=",
            "%3E": ">",
            "%3F": "?",
            "%40": "@",
            "%5C": "_",
            "%5B": "[",
            "%5D": "]",
            "%5E": "^",
            "%5F": "_",
            "%60": "`",
            "%7B": "{",
            "%7C": "_",
            "%7D": "}",
            "%7E": "~",
            "%7F": " ",
        }
        new_file_name = file_name.rsplit('/', 1)[-1]
        for key in file_name_filters:
            new_file_name = re.sub(str(key), str(file_name_filters[key]), new_file_name)
        new_file_name = re.sub("[*<>:;|/]*", "", new_file_name)
        return new_file_name

    def download_urls(self, url):
        file_name = self.clean_file_name(url)
        print(f"Downloading: {file_name} from: {url}")
        try:
            site_folder = url.rsplit('/', 1)[-2]
            site_folder = re.sub("[&*!@#$%^(), ]*", "", os.path.basename(site_folder.rstrip('/')))
            if not os.path.isdir(os.path.normpath(os.path.join(self.save_path, site_folder))):
                os.mkdir(os.path.normpath(os.path.join(self.save_path, site_folder)))
            if not os.path.isfile(os.path.normpath(os.path.join(self.save_path, site_folder, file_name))):
                with urllib.request.urlopen(url) as response, open(
                        os.path.normpath(os.path.join(self.save_path, site_folder, file_name)), 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                print(f"\tDownloaded ({self.file_urls.index(url)}/{len(self.file_urls)}): "
                      f"{os.path.normpath(os.path.join(self.save_path, site_folder, file_name))}")
            else:
                print(f"\tFile {os.path.normpath(os.path.join(self.save_path, site_folder, file_name))} "
                      f"already downloaded")
        except Exception as e:
            print(f"Unable to download: {file_name}\nError:\n{e}")
            pass

    def screenshot_urls(self, parallel_urls):
        self.launch_browser()
        for url in parallel_urls:
            self.set_zoom_level(self.zoom_level)
            try:
                self.full_page_screenshot(url=f'{url}', zoom_percentage=self.zoom_level)
            except Exception as e:
                print(f"Unable to capture screenshot\nError: {e}\nTrying again...")
                try:
                    self.full_page_screenshot(url=f'{url}', zoom_percentage=self.zoom_level)
                except Exception as e:
                    print(f"Unable to capture screenshot\nError: {e}")
            self.url_count = self.url_count + 1
            percentage = '%.3f' % ((self.url_count / len(self.urls)) * 100)
            urls_processed = '{0: <25}'.format(f"URL(s) Processed: {self.url_count}")
            percentage_display = '{0: <20}'.format(f"Percentage: {percentage}%")
            total = '{0: <15}'.format(f"Total: {self.url_count}/{len(self.urls)}")
            print(f"{urls_processed} | {percentage_display} | {total}\n")
        self.quit_driver()
        self.url_count = 0

    def screenshot_urls_in_parallel(self, parallel_urls):
        pool = Pool(processes=self.processes)
        try:
            pool.map(self.screenshot_urls, parallel_urls)
        finally:
            pool.close()
            pool.join()


def webarchiver(argv):
    filename = "./links.txt"
    image_format = 'png'
    browser = "Chrome"
    executor = "Local"
    archive = Webarchiver()
    clean_flag = False
    file_flag = False
    zoom_level = 100
    image_archive = False
    scrape_flag = False
    processes = 1
    url_filter = ['.zip', '.rar', '.tar.gz', '.gzip', '.iso', '.7z', '.7zip', '.tar', '.gz', '.txt', '.md', '.mp3',
                  '.wav', '.flac', '.mp4', '.mkv', '.m4a', '.avi', '.gif', '.jpg', '.jpeg', '.png', '.webm', '.3ds',
                  '.nds', '.bin', '.cue', '.chd', '.ndd', '.fds', '.sbl', '.rvz', '.gcz', '.cso', '.ecm', '.mds',
                  '.md5', '.sfc', '.mdf', '.img', '.ccd', '.tap', '.tzx', '.cdc', '.cas', '.nes', '.nez', '.unf',
                  '.unif', '.smc', '.md', '.smd', '.gen', '.gg', '.z64', '.v64', '.n64', '.gb', '.gbc', '.gba',
                  '.srl', '.gcm', '.gcz', '.nds', '.dsi', '.app', '.ids', '.wbfs', '.wad', '.cia', '.nsp', '.xci',
                  '.ngp', '.ngc', '.pce', '.vpk', '.vb', '.ws', '.wsc', '.ipa', '.apk', '.obb', '.dsv', '.sav',
                  '.ps2', '.mcr', '.mpk', '.eep', '.srm']

    try:
        opts, args = getopt.getopt(argv, "hb:cd:e:f:l:i:sp:u:z:", ["help", "browser=", "clean", "directory=", "dpi=",
                                                                   "file=", "executor=", "links=", "image-type=",
                                                                   "scrape", "processes=",
                                                                   "url-filter=", "zoom="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-b", "--browser"):
            browser = arg
        elif opt in ("-c", "--clean"):
            clean_flag = True
        elif opt in ("-d", "--directory"):
            archive.set_save_path(arg)
        elif opt == "--dpi":
            archive.set_dpi_level(int(arg))
        elif opt in ("-f", "--file"):
            file_flag = True
            filename = arg
        elif opt in ("-e", "--executor"):
            executor = arg
        elif opt in ("-s", "--scrape"):
            scrape_flag = True
        elif opt in ("-u", "--url-filter"):
            url_filter = arg.replace(" ", "")
            url_filter = url_filter.split(",")
        elif opt in ("-l", "--links"):
            url_list = arg.replace(" ", "")
            url_list = url_list.split(",")
            for url in url_list:
                archive.append_link(url.strip())
                archive.append_file_link(url.strip())
        elif opt in ("-i", "--image-type"):
            if arg.lower() == "png" or arg.lower() == "jpg" or arg.lower() == "jpeg":
                image_format = f'{arg.lower()}'
            image_archive = True
        elif opt in ("-p", "--processes"):
            processes = int(arg)
        elif opt in ("-z", "--zoom"):
            zoom_level = arg

    if file_flag:
        archive.open_file(filename)

    if clean_flag:
        archive.clean_url()

    if image_archive:
        archive.set_zoom_level(zoom_level)
        archive.set_image_format(image_format)
        archive.set_browser(browser=browser)
        archive.set_executor(executor=executor)
        if len(archive.urls) < processes:
            processes = len(archive.urls)
        archive.set_processes(processes=processes)
        parallel_urls = list(chunks(archive.urls, processes))
        archive.screenshot_urls_in_parallel(parallel_urls=parallel_urls)

    if scrape_flag:
        archive.set_processes(processes=processes)
        archive.set_url_filter(url_filter=url_filter)
        archive.scrape_urls_in_parallel()
        archive.download_urls_in_parallel()


def usage():
    print(f'Webarchiver: Archive the Internet!\n'
          f'Version: {__version__}\n'
          f'Author: {__author__}\n'
          f'Credits: {__credits__}\n'
          f'Usage:\n'
          f'-h | --help       [ See usage ]\n'
          f'-b | --browser    [ Specify browser: Chrome / Firefox ]\n'
          f'-c | --clean      [ Convert mobile sites to regular site ]\n'
          f'-d | --directory  [ Location where the images will be saved ]\n'
          f'     --dpi        [ DPI for the image ]\n'
          f'-e | --executor   [ Execution environment: Local / Selenoid Host|Selenoid URL ]\n'
          f'-f | --file       [ Text file to read the URL(s) from ]\n'
          f'-l | --links      [ Comma separated URL(s) ]\n'
          f'-i | --image-type [ Save images as PNG or JPEG ]\n'
          f'-p | --processes  [ Number of processes to run scrape and download ]\n'
          f'-s | --scrape     [ Scrape URL(s) by Downloading ]\n'
          f'-u | --url-filter [ Only filter for specific files that contain this string ]\n'
          f'-z | --zoom       [ The zoom to use on the browser ]\n'
          f'\n'
          f'webarchiver \\ \n'
          f'\t-c \\ \n'
          f'\t-f <links_file.txt>  \\ \n'
          f'\t-l "<URL1, URL2, URL3>" \\ \n'
          f'\t-i <JPEG/PNG> \\ \n'
          f'\t-d "~/Downloads" \\ \n'
          f'\t-z 100 \\ \n'
          f'\t--dpi 1 \\ \n'
          f'\t--browser "Chrome" \\ \n'
          f'\t--executor "selenoid|http://selenoid.com/wd/hub"\n'
          f'\n'
          f'webarchiver \\ \n'
          f'\t-s \\ \n'
          f'\t-f <links_file.txt>  \\ \n'
          f'\t-l "<URL1, URL2, URL3>" \\n')


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(2)
    webarchiver(sys.argv[1:])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(2)
    webarchiver(sys.argv[1:])
