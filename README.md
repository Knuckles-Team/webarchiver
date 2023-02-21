# Webarchiver
*Version: 0.5.0*

Python tool that allows you to take full page screenshots of pages without ads

Supports batching by adding multiple links in a text file, or my adding links to command line separated by commas.

### Requirements:
- Chrome/Chomium browser

### Usage:
| Short Flag | Long Flag    | Description                             |
|------------|--------------|-----------------------------------------|
| -h         | --help       | See Usage                               |
| -c         | --clean      | Convert mobile sites to regular site    |
| -d         | --directory  | Location where the images will be saved |
|            | --dpi        | DPI for the image                       |
| -f         | --file       | Text file to read the URLs from         |
| -l         | --links      | Comma separated URLs (No spaces)        |
| -i         | --image-type | Save images as PNG or JPEG              |
| -t         | --threads    | Number of threads to run concurrently   |
| -u         | --url-filter | Filter URLs that contain this string    |
| -z         | --zoom       | The zoom to use on the browser          |


### Example:
```bash
webarchiver -c -f <links_file.txt> -l "<URL1,URL2,URL3>" -t <JPEG/PNG> -d "~/Downloads" -z 100 --dpi 1
```

#### Install Instructions
Install Python Package

```bash
python -m pip install webarchiver
```

#### Build Instructions
Build Python Package

```bash
sudo chmod +x ./*.py
pip install .
python setup.py bdist_wheel --universal
# Test Pypi
twine upload --repository-url https://test.pypi.org/legacy/ dist/* --verbose -u "Username" -p "Password"
# Prod Pypi
twine upload dist/* --verbose -u "Username" -p "Password"
```
