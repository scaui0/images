import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path

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


class Filters:
    @staticmethod
    def without_red(r, g, b, a=255):
        return 0, g, b, a

    @staticmethod
    def without_green(r, g, b, a=255):
        return r, 0, b, a

    @staticmethod
    def without_blue(r, g, b, a=255):
        return r, g, 0, a

    @staticmethod
    def white_black(r, g, b, a=255):
        median = (r + g + b) // 3
        return median, median, median, a

    @staticmethod
    def only_red(r, g, b, a=255):
        return r, 0, 0, a

    @staticmethod
    def only_green(r, g, b, a=255):
        return 0, g, 0, a

    @staticmethod
    def only_blue(r, g, b, a=255):
        return 0, 0, b, a

    @staticmethod
    def in_three_steps(r, g, b, a=255):
        return (
            0 if r < 80 else 140 if r < 160 else 255,
            0 if g < 80 else 140 if g < 160 else 255,
            0 if b < 80 else 140 if b < 160 else 255,
            0 if a < 80 else 140 if a < 160 else 255
        )


ALL_FILTERS = {
    "WITHOUT_RED": Filters.without_red,
    "WITHOUT_GREEN": Filters.without_green,
    "WITHOUT_BLUE": Filters.without_blue,
    "ONLY_RED": Filters.only_red,
    "ONLY_GREEN": Filters.only_green,
    "ONLY_BLUE": Filters.only_blue,
    "WHITE_BLACK": Filters.white_black,
    "IN_THREE_STEPS": Filters.in_three_steps,
    "ORIGINAL": None  # Just works because if filter in filter_and_save is None, it won't be filtered and just saved
}


def try_opening_image(image_path):
    try:
        return open_image(image_path).convert("RGBA")
    except ValueError:
        print("Unsupported image mode! Can't convert it to RGBA!")
        return
    except FileNotFoundError:
        print(f"Can't find image at {image_path}!")
        return
    except UnidentifiedImageError:
        print(f"Can't load image! ({image_path})")
        return
    except PermissionError:
        if not image_path.is_dir():
            print(f"Permission denied! ({image_path})")
        return


def filter_and_save(image_path, image_filter=None, path_to_save: Path | None = None, filter_name=None, image_name=None):
    if (image := try_opening_image(image_path)) is None:
        return filter_name, image_name, False

    if image_filter is None:
        filtered_image = image
    else:
        filtered_image = filter_image(image, image_filter, copy_image=False)
    if path_to_save is not None:
        filtered_image.save(path_to_save)
    else:
        filtered_image.show()

    return filter_name, image_name, True


def filter_and_save_multiple(image_paths, image_filters, paths_to_save, sort_by_filter=None, last_paths=None):
    if not (len(image_paths) == len(image_filters) == len(paths_to_save)):
        raise IndexError("Len of images, image_filters and paths_to_save are not equals!")

    result = []
    for image_path, image_filters_for_file, path_to_save, sort_image_by_filter, last_path_for_image \
            in zip(image_paths, image_filters, paths_to_save, sort_by_filter, last_paths):

        for filter_name, image_filter in image_filters_for_file.items():
            if sort_by_filter:
                real_path_to_save = path_to_save / f"{filter_name.lower()}" / last_path_for_image
                real_path_to_save.parent.mkdir(exist_ok=True, parents=True)

            else:
                real_path_to_save = path_to_save / f"{filter_name.lower()}.png"

            result.append(
                filter_and_save(image_path, image_filter, real_path_to_save, filter_name, image_path.stem)
            )
    return result


def path_relative_or_absolute(path):
    path = Path(path)
    return path if path.is_absolute() else CURRENT_PATH / path


def split_list(input_list, x):
    k, m = divmod(len(input_list), x)

    return [input_list[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(x)]


def main():
    parser = argparse.ArgumentParser(
        "Funny File Filters",
        description="Use Funny File Filters on your image and look at the amazing result!"
    )
    parser.add_argument("input", help="The input file/folder")
    parser.add_argument("output", help="The output folder")
    parser.add_argument(
        "-f", "--filters", help="The filters to use, comma-separated. If unspecified, all will be used."
    )
    parser.add_argument(
        "-t", "--threads", type=int, default=10,
        help="The number of max processes to use. Default is 10"
    )
    parser.add_argument(
        "-s", "--sort-by-filter", action="store_true",
        help="Sorts the images by filter name."
    )
    args = parser.parse_args()

    input_path = path_relative_or_absolute(args.input)
    output_path = path_relative_or_absolute(args.output)
    max_threads = args.threads
    sort_by_filter = args.sort_by_filter

    print(f"Input file/folder: {input_path}")
    print(f"Output folder: {output_path}")

    if args.filters is None:
        filters_to_apply = ALL_FILTERS
    else:
        filters_to_apply = {}
        for filter_name in args.filters.split(","):
            if filter_name in ALL_FILTERS:
                filters_to_apply[filter_name] = ALL_FILTERS[filter_name]
            else:
                print(f"Invalid filter {filter_name}! Ignoring it")

    print(f"Specified filters: {','.join(filters_to_apply.keys())}")
    print(f"Sort by filters: {sort_by_filter}")

    if isinstance(max_threads, int):
        if max_threads <= 0:
            parser.error("Argument 'threads' must be positive!")
            return
        elif max_threads > 61:
            parser.error("Argument 'threads' must be less than or equals than 61!")

    start_time = datetime.now()

    task_arguments = []
    if input_path.is_file():
        task_arguments.append(
            (input_path, filters_to_apply, output_path, sort_by_filter)
        )

    elif input_path.is_dir():
        for sub_file in input_path.rglob("*"):
            relativ_to_input_path = sub_file.relative_to(input_path)

            if sort_by_filter:
                output_path_for_filtered_images = output_path  # Can't do it here. It's done in filter_and_save_multiple
            else:
                output_path_for_filtered_images = output_path / relativ_to_input_path

            output_path_for_filtered_images.mkdir(exist_ok=True)

            task_arguments.append(
                (sub_file, filters_to_apply, output_path_for_filtered_images, sort_by_filter, relativ_to_input_path)
            )


    def prepare_arguments_for_task(arguments):
        return [
            [[x[0] for x in arguments[chunk]]]
            + [[x[1] for x in arguments[chunk]]]
            + [[x[2] for x in arguments[chunk]]]
            + [[x[3] for x in arguments[chunk] if len(x) >= 3]]
            + [[x[4] for x in arguments[chunk] if len(x) >= 3]]
            for chunk in range(len(arguments))
        ]

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_threads) as executor:
        chunked = split_list(task_arguments, max_threads)
        corrected = prepare_arguments_for_task(chunked)

        futures = []
        for args in corrected:
            if args:
                futures.append(
                    executor.submit(
                        filter_and_save_multiple, *args
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
