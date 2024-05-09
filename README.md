# Webarchiver

![PyPI - Version](https://img.shields.io/pypi/v/webarchiver)
![PyPI - Downloads](https://img.shields.io/pypi/dd/webarchiver)
![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/webarchiver)
![GitHub forks](https://img.shields.io/github/forks/Knuckles-Team/webarchiver)
![GitHub contributors](https://img.shields.io/github/contributors/Knuckles-Team/webarchiver)
![PyPI - License](https://img.shields.io/pypi/l/webarchiver)
![GitHub](https://img.shields.io/github/license/Knuckles-Team/webarchiver)

![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/webarchiver)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Knuckles-Team/webarchiver)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Knuckles-Team/webarchiver)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/webarchiver)

![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/webarchiver)
![GitHub language count](https://img.shields.io/github/languages/count/Knuckles-Team/webarchiver)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/webarchiver)
![GitHub repo file count (file type)](https://img.shields.io/github/directory-file-count/Knuckles-Team/webarchiver)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/webarchiver)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/webarchiver)

*Version: 0.32.7*

Python tool that allows you to take full page screenshots of pages without ads

Supports batching by adding multiple links in a text file, or my adding links to command line separated by commas.

This repository is actively maintained - Contributions are welcome!

#### Requirements:

One of the following browsers:

- Chrome/Chromium browser
- Firefox
- Selenoid Server

<details>
  <summary><b>Usage:</b></summary>

| Short Flag | Long Flag    | Description                                                |
|------------|--------------|------------------------------------------------------------|
| -h         | --help       | See Usage                                                  |
| -b         | --browser    | Specify browser: Chrome / Firefox / Selenoid               |
| -c         | --clean      | Convert mobile sites to regular site                       |
| -d         | --directory  | Location where the images will be saved                    |
|            | --dpi        | DPI for the image                                          |
| -e         | --executor   | Execution environment: Local / Selenoid Host\|Selenoid URL |
| -f         | --file       | Text file to read the URL(s) from                          |
| -l         | --links      | Comma separated URL(s)                                     |
| -i         | --image-type | Save images as PNG or JPEG                                 |
| -p         | --processes  | Number of processes to run concurrently                    |
| -s         | --scrape     | Scrape URL(s) by Downloading                               |
| -u         | --url-filter | Filter URL(s) that contain this string                     |
| -z         | --zoom       | The zoom to use on the browser                             |

</details>

<details>
  <summary><b>Example:</b></summary>

```bash
webarchiver -c -f <links_file.txt> -l "<URL1,URL2,URL3>" -i 'jpeg' -d "~/Downloads" -z 100 --dpi 1 --browser "Firefox"
```

```bash
webarchiver -c -f <links_file.txt> -l "<URL1,URL2,URL3>" -i 'png' -d "~/Downloads" -z 100 --dpi 1 --executor "selenoid|http://selenoid.com/wd/hub" --browser "Chrome"
```

```bash
webarchiver -s -f <links_file.txt> -l "<URL1,URL2,URL3>"
```

</details>

<details>
  <summary><b>Installation Instructions:</b></summary>

Install Python Package

```bash
python -m pip install webarchiver
```

</details>


## Geniusbot Application

Use with a GUI through Geniusbot

Visit our [GitHub](https://github.com/Knuckles-Team/geniusbot) for more information

<details>
  <summary><b>Installation Instructions with Geniusbot:</b></summary>

Install Python Package

```bash
python -m pip install geniusbot
```

</details>

<details>
  <summary><b>Repository Owners:</b></summary>


<img width="100%" height="180em" src="https://github-readme-stats.vercel.app/api?username=Knucklessg1&show_icons=true&hide_border=true&&count_private=true&include_all_commits=true" />

![GitHub followers](https://img.shields.io/github/followers/Knucklessg1)
![GitHub User's stars](https://img.shields.io/github/stars/Knucklessg1)
</details>
