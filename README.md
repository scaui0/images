# Funny File Filters Documentation

## Overview
Funny File Filters is a Python program that applies various filters to images in a specified directory and saves the results. The program supports multiple filters, parallel processing, and handling of non-image files using templates or copying.

## Installing

* If not done yet, install Python from the [official website](https://www.python.org/)
* To install all dependencies, open a terminal go to the program folder using `cd` command and run `pip install -r requirements.txt`.
   If you get a message `pip` command is missing, try running `python -m pip install -r requirements.txt`. If it still doesn't work, read the error messages.

## Usage
To run the program, use the following command:

```
python funny_file_filters.py [OPTIONS] INPUT OUTPUT
```

### Arguments
- `INPUT`: The input file or folder containing images to be processed.
- `OUTPUT`: The output folder where the processed images will be saved.

### Options
- `-f, --filters`: Comma-separated list of filters to apply. If unspecified, all filters will be used. Available filters are: `WITHOUT_RED`, `WITHOUT_GREEN`, `WITHOUT_BLUE`, `ONLY_RED`, `ONLY_GREEN`, `ONLY_BLUE`, `WHITE_BLACK`, `IN_THREE_STEPS`, `ORIGINAL`, `INVERT`.
- `-p, --processes`: The maximum number of processes to use. Default is 10.
- `-s, --sort-by-filter`: Sorts the images by filter name.
- `-c, --copy-other-files`: Copy non-image files into the corresponding location in the output folder.
- `-t, --use-template`: Use a template on non-image files and save them in the output folder.
   Templates support the following substitutions (with example in parentheses):
   `$FILTER(black white)`, `$FILTER_UPPER(BLACK_WHITE)`, and `$FILTER_LOWER(black_white)`.
   You can also use the syntax `${<FILTER,FILTER_UPPER or FILTER_LOWER>}`.
- `-e, --other-file-encoding`: Encoding to use on non-image files.

## Filters
The program supports the following filters:
- `WITHOUT_RED`: Removes the red channel.
- `WITHOUT_GREEN`: Removes the green channel.
- `WITHOUT_BLUE`: Removes the blue channel.
- `WHITE_BLACK`: Converts the image to grayscale.
- `ONLY_RED`: Keeps only the red channel.
- `ONLY_GREEN`: Keeps only the green channel.
- `ONLY_BLUE`: Keeps only the blue channel.
- `IN_THREE_STEPS`: Converts the image colors to three levels: 0, 140, and 255.
- `INVERT`: Inverts the image colors.
- `ORIGINAL`: Keeps the image unchanged.

## Examples
### Example 1: Apply all filters to a single image
```
python funny_file_filters.py -p 5 input_image.jpg output_folder
```
This command will apply all filters to `input_image.jpg` using up to 5 parallel processes and save the results in `output_folder`.


### Example 2: Apply specific filters to all images in a folder
```
python funny_file_filters.py -f WITHOUT_RED,WHITE_BLACK input_folder output_folder
```
This command will apply the `WITHOUT_RED` and `WHITE_BLACK` filters to all images in `input_folder` and save the results in `output_folder`.


### Example 3: Copy non-image files
```
python funny_file_filters.py -c input_folder output_folder
```
This command will copy all non-image files from `input_folder` to `output_folder`.
All image files will be processed normally.


### Example 4: Use template on non-image files
```
python funny_file_filters.py -t -e utf-8 input_folder output_folder
```
This command will apply templates to all non-image files in `input_folder`, using `utf-8` encoding, and save the results in `output_folder`.
All image files will be processed normally.
