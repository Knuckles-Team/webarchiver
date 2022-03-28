#!/usr/bin/env python
# coding: utf-8

from setuptools import setup

setup(
    name='webarchive',
    version="0.1.0",
    description='Python tool that allows you to take multiple full page screenshots of web pages without ads.',
    url='https://github.com/Knucklessg1/webarchive',
    author='Audel Rouhi',
    author_email='knucklessg1@gmail.com',
    license='Unlicense',
    packages=[],
    install_requires=['selenium', 'Pillow', 'webdriver-manager', 'piexif'],
    scripts=['webarchive.py', 'webarchive'],
    package_data={'webarchive': ['webarchive']},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: Public Domain',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)