import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path

from PIL import UnidentifiedImageError
from PIL.Image import open as open_image, fromarray


CURRENT_PATH = Path(__file__).parent


def filter_image(image, filter_function, copy_image=True):
    if copy_image:
        image = image.copy()

    for x in range(image.width):
        for y in range(image.height):
            image.putpixel((x, y), filter_function(*image.getpixel((x, y))))

    return image


class Filters:
    @staticmethod
    def _without_helper(
            r, g, b, a,
            has_r=True, has_g=True, has_b=True, has_a=True
    ):
        return (
            r if has_r else 0,
            g if has_g else 0,
            b if has_b else 0,
            a if has_a else 0
        )

    @staticmethod
    def without_red(r, g, b, a):
        return 0, g, b, a

    @staticmethod
    def without_green(cls, r, g, b, a):
        return r, 0, b, a

    @staticmethod
    def without_blue(r, g, b, a):
        return r, g, 0, a

    @staticmethod
    def white_black(r, g, b, a):
        median = (r + g + b) // 3
        return median, median, median, a

    @staticmethod
    def only_red(r, g, b, a):
        return r, 0, 0, a

    @staticmethod
    def only_green(r, g, b, a):
        return 0, g, 0, a

    @staticmethod
    def only_blue(r, g, b, a):
        return 0, 0, b, a

    @staticmethod
    def in_three_steps(r, g, b, a):
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


def filter_and_save(image, image_filter=None, path_to_save: Path | None = None, filter_name=None, image_name=None):
    if image_filter is None:
        filtered_image = image
    else:
        filtered_image = filter_image(image, image_filter, copy_image=False)
    if path_to_save is not None:
        filtered_image.save(path_to_save)
    else:
        filtered_image.show()

    return filter_name, image_name


def main():
    def path_relative_or_absolute(path):
        path = Path(path)
        return path if path.is_absolute() else CURRENT_PATH / path

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
            print("Can't load image!")
            return

    parser = argparse.ArgumentParser(
        "Funny File Filters",
        description="Use Funny File Filters on your image and look at the amazing result!"
    )
    parser.add_argument("input", help="The input file/folder")
    parser.add_argument("output", help="The output folder")
    parser.add_argument(
        "-f", "--filters", help="The filters to use, comma-separated. If unspecified, all will be used."
    )
    parser.add_argument("-t", "--threads", type=int, default=10, help="The number of max threads to use. Default is 10")
    args = parser.parse_args()

    input_path = path_relative_or_absolute(args.input)
    output_path = path_relative_or_absolute(args.output)
    max_threads = args.threads

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

    start_time = datetime.now()

    task_arguments = []
    if input_path.is_file():
        original_image = try_opening_image(input_path)
        if original_image is not None:
            for filter_name, image_filter in filters_to_apply.items():
                task_arguments.append((
                    original_image.copy(),
                    image_filter, output_path / f"{filter_name.lower()}.png",
                    filter_name,
                    input_path.stem
                ))

    elif input_path.is_dir():
        for sub_file in input_path.iterdir():
            if sub_file.suffix.lower() not in (".png", ".jpg"):
                print(f"File {sub_file} has wrong suffix {sub_file.suffix}!")
                continue

            original_image = try_opening_image(sub_file)
            if original_image is None:
                continue

            output_path_for_filtered_images = Path(output_path, sub_file.stem)
            output_path_for_filtered_images.mkdir(exist_ok=True)

            for filter_name, image_filter in filters_to_apply.items():
                task_arguments.append((
                    original_image.copy(),
                    image_filter,
                    output_path_for_filtered_images / f"{filter_name.lower()}.png",
                    filter_name,
                    sub_file.stem
                ))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for arguments in task_arguments:
            futures.append(
                executor.submit(
                    filter_and_save, *arguments
                )
            )

        print(f"Threads ({len(futures)} in total) are in the queue")
        print("Waiting for threads...")
        print()
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            future_name, file_name = future.result()
            if future_name is not None and file_name is not None:  # Default if no errors are in code
                print(f"Thread {i}/{len(futures)} ({future_name} for file {file_name!r}) is done!")
            else:
                print(f"Thread {i}/{len(futures)} is done!")

        print("All threads are done!")
        print(f"Filtering took {(datetime.now() - start_time).total_seconds()} seconds!")
        print(
            f"To see the result of Funny File Filters, open the generated images in the output folder ({output_path})"
        )


if __name__ == '__main__':
    main()
