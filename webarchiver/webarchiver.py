#!/usr/bin/env python3
# coding: utf-8

import sys
import getopt
import time
import os
import math
import re
import piexif
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageChops
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


class Webarchiver:
    home = os.path.expanduser("~")
    SAVE_PATH = os.path.join(home, "Downloads")
    driver = []
    capabilities = None
    chrome_options = webdriver.ChromeOptions()
    DEFAULT_IMAGE_FORMAT = 'PNG'
    DEFAULT_IMAGE_QUALITY = 80
    urls = []
    twitter_urls = []
    twitter_df = None
    HIDDEN_SCROLL_BAR = 'hidden'
    DEFAULT_SCROLL_BAR = 'visible'
    screenshot_success = False
    screenshot_success_alt = False
    zoom_level = 100
    dpi = 1.0
    max_scroll_height = 369369

    def __init__(self):
        pass

    def launch_browser(self):
        self.capabilities = {
            'self.browserName': 'chrome',
            'chromeOptions': {
                'useAutomationExtension': False,
                'forceDevToolsScreenshot': True
            }
        }
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
        if self.dpi != 1:
            self.chrome_options.add_argument(f'--force-device-scale-factor={self.dpi}')
            self.chrome_options.add_argument(f'--high-dpi-support={self.dpi}')
        try:
            self.driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(),
                                           desired_capabilities=self.capabilities,
                                           options=self.chrome_options)
            # Hide the scrollbar
            scrollbar_js = 'document.documentElement.style.overflow = \"{}\"'.format(self.HIDDEN_SCROLL_BAR)
            self.driver.execute_script(scrollbar_js)
        except Exception as e:
            print("Could not open with Latest Chrome Version. PLEASE ENSURE YOU'RE NOT RUNNING WITH SUDO", e)
            exit()

    def open_file(self, file):
        webarchive_urls = open(file, 'r')
        for url in webarchive_urls:
            self.append_link(url)

    def append_link(self, url):
        print(f"URL Appended: {url}")
        self.urls.append(url)
        self.urls = list(dict.fromkeys(self.urls))

    def get_links(self):
        return self.urls

    def reset_links(self):
        print("Links Reset")
        self.urls = []

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

    def screenshot(self, url, zoom_percentage=100, filename=None, filetype=DEFAULT_IMAGE_FORMAT,
                   quality=DEFAULT_IMAGE_QUALITY):
        self.read_url(url, zoom_percentage)
        print(f"Quality: {quality}")
        if filename:
            title = re.sub('[\\\\/:"*?<>|\']', '', filename)
            title = (title[:140]) if len(title) > 140 else title
            self.driver.save_screenshot(f'{self.SAVE_PATH}/{title}.{filetype}')
        else:
            print(f"Driver Title: {self.driver.title}")
            print(f"URL, {url}")
            if self.driver.title:
                title = re.sub('[\\\\/:"*?<>|\']', '', self.driver.title)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
                self.driver.save_screenshot(f'{self.SAVE_PATH}/{title}.{filetype}')
            else:
                title = re.sub('[\\\\/:"*?<>|.,\']', '', url)
                title = title.replace(" ", "_")
                title = (title[:140]) if len(title) > 140 else title
                self.driver.save_screenshot(f'{self.SAVE_PATH}/{title}.{filetype}')

    def fullpage_screenshot(self, url, zoom_percentage=100, filename=None, filetype=DEFAULT_IMAGE_FORMAT,
                            quality=DEFAULT_IMAGE_QUALITY):
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
        image_options['format'] = filetype
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
            image_file.save(f'{self.SAVE_PATH}/{title}.{filetype}', **image_options)
            self.screenshot_success = True
        except Exception as e:
            print("Could not save image error: ", e)
            try:
                os.remove(f'{self.SAVE_PATH}/{title}.{filetype}')
            except Exception as e:
                print(f"Could not remove file, does it exist? {e}")
            self.screenshot_success = False

        y_offset_js = 'return window.pageYOffset;'
        new_offset = self.driver.execute_script(y_offset_js)

        if initial_offset != new_offset:
            self.driver.execute_script(scroll_to_js.format(initial_offset))

        if not self.screenshot_success:
            self.fullpage_screenshot_alternative(url=f'{url}', zoom_percentage=zoom_percentage, filename=f'{title}',
                                                 filetype=filetype, quality=quality)

    def fullpage_screenshot_alternative(self, url, zoom_percentage=100, filename=None, **kwargs):
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
        image_options['format'] = kwargs.get('format') or self.DEFAULT_IMAGE_FORMAT
        image_options['quality'] = kwargs.get('quality') or self.DEFAULT_IMAGE_QUALITY
        filetype = kwargs.get('format') or self.DEFAULT_IMAGE_FORMAT
        quality = kwargs.get('quality') or self.DEFAULT_IMAGE_QUALITY
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
        print(f"Saving image to: {self.SAVE_PATH}/{filename}.{filetype}'")
        try:
            stitched_image.save(f"{self.SAVE_PATH}/{filename}.{filetype}", **image_options)
            self.screenshot_success_alt = True
        except Exception as e:
            print("Could not save image error in alternative form: ", e)
            try:
                os.remove(f'{self.SAVE_PATH}/{filename}.{filetype}')
            except Exception as e:
                print(f"Could not remove file, does it exist? {e}")
            self.screenshot_success_alt = False

        print("Finishing chrome full page screenshot workaround...")
        if not ImageChops.invert(stitched_image).getbbox() or not stitched_image.getbbox() or self.screenshot_success_alt is False:
            print("Could not save full page screenshot, saving single page screenshot instead")
            self.screenshot(url=f'{url}', zoom_percentage=zoom_percentage, filename=filename, filetype=filetype,
                            quality=quality)

    def set_save_path(self, save_path):
        self.SAVE_PATH = save_path
        self.SAVE_PATH = self.SAVE_PATH.replace(os.sep, '/')
        print(f"Save Path: {self.SAVE_PATH }")
        if save_path is None or save_path == "":
            self.SAVE_PATH = f"{os.path.expanduser('~')}".replace("\\", "/")
        if not os.path.exists(self.SAVE_PATH):
            os.makedirs(self.SAVE_PATH)

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
                self.driver.execute_script("""(function () {
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
                self.driver.execute_script("""(function () { 
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
                self.driver.execute_script("""(function () {
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
                self.driver.execute_script("""(function () {
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
        body = self.driver.find_element_by_xpath('/html/body')
        self.driver.execute_script("arguments[0].setAttribute('style', 'overflow: scroll; overflow-x: scroll')", body)
        html = self.driver.find_element_by_xpath('/html')
        self.driver.execute_script("arguments[0].setAttribute('style', 'overflow: scroll; overflow-x: scroll')", html)
        print("Set scrolls override")

    def quit_driver(self):
        print("Chrome Driver Closed")
        self.driver.quit()


def webarchiver(argv):
    filename = "./links.txt"
    archive = Webarchiver()
    clean_flag = False
    file_flag = False
    zoom_level = 100

    try:
        opts, args = getopt.getopt(argv, "hcd:f:l:t:z:", ["help", "clean", "directory=", "dpi=", "file=", "links=",
                                                          "type=", "zoom="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-c", "--clean"):
            clean_flag = True
        elif opt in ("-d", "--directory"):
            archive.set_save_path(arg)
        elif opt == "--dpi":
            archive.set_dpi_level(int(arg))
        elif opt in ("-f", "--file"):
            file_flag = True
            filename = arg
        elif opt in ("-l", "--links"):
            url_list = arg.replace(" ", "")
            url_list = url_list.split(",")
            for url in url_list:
                archive.append_link(url)
        elif opt in ("-t", "--type"):
            if arg == "PNG" or arg == "png" or arg == "JPG" or arg == "jpg" or arg == "JPEG" or arg == "jpeg":
                archive.DEFAULT_IMAGE_FORMAT = f'{arg}'
        elif opt in ("-z", "--zoom"):
            zoom_level = arg

    if file_flag:
        archive.open_file(filename)

    if clean_flag:
        archive.clean_url()

    archive.launch_browser()
    url_count = 0
    for url in archive.urls:
        archive.set_zoom_level(zoom_level)
        archive.fullpage_screenshot(url=f'{url}', zoom_percentage=zoom_level)
        url_count = url_count + 1
        percentage = '%.3f' % ((url_count/len(archive.urls))*100)
        urls_processed = '{0: <25}'.format(f"URLs Processed: {url_count}")
        percentage_display = '{0: <20}'.format(f"Percentage: {percentage}%")
        total = '{0: <15}'.format(f"Total: {url_count}/{len(archive.urls)}")
        print(f"{urls_processed} | {percentage_display} | {total}\n")

    archive.quit_driver()


def usage():
    print(f'Usage:\n'
          f'-h | --help      [ See usage ]\n'
          f'-c | --clean     [ Convert mobile sites to regular site ]\n'
          f'-d | --directory [ Location where the images will be saved ]\n'
          f'     --dpi       [ DPI for the image ]\n'
          f'-f | --file      [ Text file to read the URLs from ]\n'
          f'-l | --links     [ Comma separated URLs (No spaces) ]\n'
          f'-t | --type      [ Save images as PNG or JPEG ]\n'
          f'-z | --zoom      [ The zoom to use on the browser ]\n'
          f'\n'
          f'webarchiver -c -f <links_file.txt> '
          '-l "<URL1, URL2, URL3>" -t <JPEG/PNG> -d "~/Downloads" -z 100 --dpi 1\n')


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
