import argparse
import concurrent.futures
import enum
from datetime import datetime
from pathlib import Path
from string import Template

import encodings.aliases
from PIL import UnidentifiedImageError
from PIL.Image import open as open_image


CURRENT_PATH = Path(__file__).parent


def filter_image(image, filter_function, copy_image=True):
    if copy_image:
        image = image.copy()

    for x in range(image.width):
        for y in range(image.height):
            pixel_color = image.getpixel((x, y))

            image.putpixel((x, y), filter_function(*pixel_color))

    return image


class Filter:
    ALL = {}

    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        func.name = self.name
        Filter.ALL[self.name] = func
        return func


class Filters:
    @staticmethod
    @Filter("WITHOUT_RED")
    def without_red(r, g, b, a=255):
        return 0, g, b, a

    @staticmethod
    @Filter("WITHOUT_GREEN")
    def without_green(r, g, b, a=255):
        return r, 0, b, a

    @staticmethod
    @Filter("WITHOUT_BLUE")
    def without_blue(r, g, b, a=255):
        return r, g, 0, a

    @staticmethod
    @Filter("WHITE_BLACK")
    def white_black(r, g, b, a=255):
        median = (r + g + b) // 3
        return median, median, median, a

    @staticmethod
    @Filter("ONLY_RED")
    def only_red(r, g, b, a=255):
        return r, 0, 0, a

    @staticmethod
    @Filter("ONLY_GREEN")
    def only_green(r, g, b, a=255):
        return 0, g, 0, a

    @staticmethod
    @Filter("ONLY_BLUE")
    def only_blue(r, g, b, a=255):
        return 0, 0, b, a

    @staticmethod
    @Filter("IN_THREE_STEPS")
    def in_three_steps(r, g, b, a=255):
        return (
            0 if r < 80 else 140 if r < 160 else 255,
            0 if g < 80 else 140 if g < 160 else 255,
            0 if b < 80 else 140 if b < 160 else 255,
            0 if a < 80 else 140 if a < 160 else 255
        )

    @staticmethod
    @Filter("INVERT")
    def invert(r, g, b, a=255):
        return 255 - r, 255 - g, 255 - b, a
    
    @staticmethod
    @Filter("ORIGINAL")
    def original(r, g, b, a=255):
        return r, g, b, a


def try_opening_image(image_path):
    try:
        return open_image(image_path).convert("RGBA")
    except ValueError:
        print(f"Unsupported image mode! Can't convert it to RGBA! ({image_path})")
    except FileNotFoundError:
        print(f"Can't find image at {image_path}!")
    except UnidentifiedImageError:
        print(f"Can't load image! ({image_path})")
    except PermissionError:
        if not image_path.is_dir():
            print(f"Permission denied! ({image_path})")


def filter_and_save(
        image_path: Path, image_filter=None, path_to_save: Path | None = None, filter_name=None, image_name=None,
        other_files=False, encoding_for_other_files=None
):
    if (image := try_opening_image(image_path)) is None:
        if other_files == OtherFileActions.copy:
            path_to_save.with_suffix(image_path.suffix).write_bytes(image_path.read_bytes())
            return "COPIED", image_name, True
        elif other_files == OtherFileActions.template:
            try:
                path_to_save.with_suffix(image_path.suffix).write_text(
                    Template(
                        image_path.read_text(encoding=encoding_for_other_files)
                    ).safe_substitute(
                        dict(
                            FILTER_UPPER=filter_name, FILTER_LOWER=filter_name.lower(),
                            FILTER=filter_name.lower().replace("_", " ")
                        )
                    ),
                    encoding=encoding_for_other_files
                )
                return "TEMPLATED", image_name, True
            except UnicodeDecodeError:
                pass
            return "TEMPLATED", image_name, False

        else:
            return filter_name, image_name, False

    if image_filter is None:
        filtered_image = image
    else:
        filtered_image = filter_image(image, image_filter, copy_image=False)
    if path_to_save is not None:
        filtered_image.save(path_to_save.with_suffix(".png"))
    else:
        filtered_image.show()

    return filter_name, image_name, True


def filter_and_save_multiple(args, other_files, encoding_for_other_files):
    result = []
    for image_path, image_filters, path_to_save, sort_by_filter, path_extension in args:
        for filter_name, image_filter in image_filters.items():
            if image_path.is_dir():
                continue
            if sort_by_filter:
                end_path_to_save = path_to_save / f"{filter_name.lower()}" / path_extension
                end_path_to_save.parent.mkdir(exist_ok=True, parents=True)
            else:
                end_path_to_save = path_to_save / f"{filter_name.lower()}.png"  # The last suffix is redundancy. It's overriden filter_and_save

            result.append(
                filter_and_save(
                    image_path, image_filter, end_path_to_save, filter_name, image_path.stem,
                    other_files, encoding_for_other_files
                )
            )
    return result


def path_relative_or_absolute(path, path_start):
    """Converts a relative or absolute path to an absolute path.

    When an absolute path must be joined, it joins path_start and path.

    :param path_start:
    :param path: The relative or absolute path of the path.
    :return: The input path converted to an absolute path.
    """
    path = Path(path)
    return path if path.is_absolute() else path_start / path


def split_list(input_list, x):
    k, m = divmod(len(input_list), x)

    return [input_list[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(x)]


class OtherFileActions(enum.Enum):
    template = enum.auto()
    dont_copy = enum.auto()
    copy = enum.auto()


def main():
    parser = argparse.ArgumentParser(
        "Funny File Filters",
        description="Use Funny File Filters on your image and look at the amazing result!"
    )
    parser.add_argument("input", help="The input file/folder")
    parser.add_argument("output", help="The output folder")
    parser.add_argument(
        "-f", "--filters",
        help="The filters to use, comma-separated. If unspecified, all will be used. Available filters are: " +
             ",".join(Filter.ALL.keys()),
    )
    parser.add_argument(
        "-p", "--processes", type=int, default=10,
        help="The number of max processes to use. Default is 10."
    )
    parser.add_argument(
        "-s", "--sort-by-filter", action="store_true",
        help="Sorts the images by filter name."
    )
    other_files_argument = parser.add_mutually_exclusive_group()
    other_files_argument.add_argument(
        "-c", "--copy-other-files", action="store_true",
        help="Copy non-image files into the corresponding location in the output folder."
    )
    other_files_argument.add_argument(
        "-t", "--use-template", action="store_true",
        help="Use template on non-image files and save them in the output folder. "
             "Templates with example result: "
             "$FILTER(black white), $FILTER_UPPER(BLACK_WHITE) and $FILTER_LOWER(black_white). "
             "You can also use the syntax ${<filter name>}"
    )
    parser.add_argument(
        "-e", "--other-file-encoding",
        help="Encoding to use on non-image files."
    )
    args = parser.parse_args()

    input_path = path_relative_or_absolute(args.input, CURRENT_PATH)
    output_path = path_relative_or_absolute(args.output, CURRENT_PATH)
    max_processes = args.processes
    sort_by_filter = args.sort_by_filter

    keep_other_files = args.copy_other_files
    use_template_on_other_files = args.use_template
    other_file_encoding = args.other_file_encoding


    if not input_path.exists():  # If output_path doesn't exist, it will be created automatically.
        parser.error(f"Input path does not exist! {input_path}")

    print(f"Input file/folder: {input_path}")
    print(f"Output folder: {output_path}")

    if args.filters is None:
        filters_to_apply = Filter.ALL
    else:
        filters_to_apply = {}
        for filter_name in args.filters.split(","):
            if filter_name in Filter.ALL:
                filters_to_apply[filter_name] = Filter.ALL[filter_name]
            else:
                print(f"Invalid filter {filter_name}! Ignoring it")

    print(f"Specified filters: {','.join(filters_to_apply.keys())}")
    print(f"Sort output by filters: {sort_by_filter}")

    if keep_other_files:
        other_files = OtherFileActions.copy
        print("Non-image files will be copied into the output folder.")
    elif use_template_on_other_files:
        other_files = OtherFileActions.template
        print("A template will be applied to all non-image files.")
    else:
        other_files = OtherFileActions.dont_copy
        print("Non-image files won't be copied.")

    if other_file_encoding not in [None] + list(encodings.aliases.aliases.values()):
        parser.error(
            "Argument 'other-file-encodings' must be unset or one of these values: "
            f"{set(encodings.aliases.aliases.values())}"
        )

    if isinstance(max_processes, int):
        if max_processes <= 0:
            parser.error("Argument 'processes' must be positive!")
        elif max_processes > 61:
            parser.error("Argument 'processes' must be less than or equals than 61!")

    start_time = datetime.now()

    task_arguments = []
    if input_path.is_file():
        for filter_name, image_filter in filters_to_apply.items():
            task_arguments.append(
                (input_path, {filter_name: image_filter}, output_path, sort_by_filter, Path())
            )

    elif input_path.is_dir():
        for sub_file in input_path.rglob("*"):
            relativ_to_input_path = sub_file.relative_to(input_path)

            if sort_by_filter:
                output_path_for_filtered_images = output_path  # Can't join the save path here. It's done in
                # filter_and_save_multiple
            else:
                output_path_for_filtered_images = output_path / relativ_to_input_path

            output_path_for_filtered_images.mkdir(exist_ok=True, parents=True)

            for filter_name, image_filter in filters_to_apply.items():
                task_arguments.append(
                    (sub_file, {filter_name: image_filter}, output_path_for_filtered_images, sort_by_filter, relativ_to_input_path)
                )
    else:
        print()
        parser.error(f"Error: Input file is neither file nor folder. It is {input_path}")

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_processes) as executor:
        chunked = split_list(task_arguments, max_processes)

        futures = []
        for args in chunked:
            if args:
                futures.append(
                    executor.submit(
                        filter_and_save_multiple, args, other_files, other_file_encoding
                    )
                )

        print(f"Threads ({len(futures)} in total) are in the queue")
        print("Waiting for threads...")
        print()
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):  # TODO: Fix numeration
            for future_name, file_name, was_successful in future.result():
                if future_name is not None and file_name is not None:  # Default if no errors are in code
                    print(f"Thread {i}/{len(futures)} ({future_name} for file {file_name!r}) is done!")
                else:
                    print(f"Thread {i}/{len(futures)} is done!")

        print("All threads are done!")
        print(f"Filtering took {(datetime.now() - start_time).total_seconds()} seconds!")
        print(
            f"Output saved in folder {output_path}"
        )
        # Old message:
        # f"To see the result of Funny File Filters,
        # open the generated images in the output folder ({output_path})"


if __name__ == '__main__':
    main()
