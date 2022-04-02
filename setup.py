#!/usr/bin/env python
# coding: utf-8

from setuptools import setup

version = "0.1.7"

setup(
    name='webarchiver',
    version=f"{version}",
    description='Python tool that allows you to take multiple full page screenshots of web pages without ads.',
    long_description=f'''# Webarchive
*Version {version}*

Python tool that allows you to take full page screenshots of pages without ads

Supports batching by adding multiple links in a text file, or my adding links to command line separated by commas.

### Requirements:
- Chrome/Chomium browser

### Usage:
| Short Flag | Long Flag   | Description                             |
|------------|-------------|-----------------------------------------|
| -h         | --help      | See Usage                               |
| -c         | --clean     | Convert mobile sites to regular site    |
| -d         | --directory | Location where the images will be saved |
|            | --dpi       | DPI for the image                       |
| -f         | --file      | Text file to read the URLs from         |
| -l         | --links     | Comma separated URLs (No spaces)        |
| -t         | --type      | Save images as PNG or JPEG              |
| -z         | --zoom      | The zoom to use on the browser          |


### Example:
```bash
webarchiver -c -f <links_file.txt> -l "<URL1,URL2,URL3>" -t <JPEG/PNG> -d "~/Downloads" -z 100 --dpi 1
```

#### Build Instructions
Build Python Package

```bash
sudo chmod +x ./*.py
sudo pip install .
python3 setup.py bdist_wheel --universal
# Test Pypi
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# Prod Pypi
twine upload dist/*
```''',
    long_description_content_type='text/markdown',
    url='https://github.com/Knucklessg1/webarchive',
    author='Audel Rouhi',
    author_email='knucklessg1@gmail.com',
    license='Unlicense',
    packages=[],
    install_requires=['selenium', 'Pillow', 'webdriver-manager', 'piexif'],
    scripts=['webarchiver.py', 'webarchiver'],
    package_data={'webarchiver': ['webarchiver']},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: Public Domain',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
