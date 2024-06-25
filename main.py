import argparse
import concurrent.futures
from pathlib import Path

from PIL import UnidentifiedImageError
from PIL.Image import open as open_image


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

    @classmethod
    def without_red(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_r=False)

    @classmethod
    def without_green(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_g=False)

    @classmethod
    def without_blue(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_b=False)

    @staticmethod
    def white_black(r, g, b, a):
        return *((((r + g + b) // 3),) * 3), a

    @classmethod
    def only_red(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_g=False, has_b=False)

    @classmethod
    def only_green(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_r=False, has_b=False)

    @classmethod
    def only_blue(cls, r, g, b, a):
        return cls._without_helper(r, g, b, a, has_g=False, has_r=False)

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
    "ORIGINAL": None  # TODO: Is it a good idea to do it so?
}


def filter_and_save(image, image_filter=None, path_to_save=None, filter_name=None):
    if image_filter is None:
        filtered_image = image
    else:
        filtered_image = filter_image(image, image_filter, copy_image=False)
    if path_to_save is not None:
        filtered_image.save(path_to_save)
    else:
        filtered_image.show()

    return filter_name


def main():
    def path_relative_or_absolute(path):
        path = Path(path)
        return path if path.is_absolute() else CURRENT_PATH / path

    def submit_actions_for_single_file(executor, filters_to_apply, input_path, output_path):
        if input_path.suffix not in (".png", ".jpg"):
            print(f"{input_path} has wrong suffix! Skipping it")
            return

        try:
            original_image = open_image(input_path).convert("RGBA")
        except ValueError:
            print("Unsupported image mode! Can't convert it to RGBA!")
            return
        except FileNotFoundError:
            print(f"Can't find image at {input_path}! Make sure it is there and restart the program!")
            return
        except UnidentifiedImageError:
            print("Can't load image!")
            return

        futures = {}
        for filter_name, image_filter in filters_to_apply.items():
            futures[filter_name] = executor.submit(
                filter_and_save,
                original_image.copy(), image_filter, output_path / f"{filter_name.lower()}.png", filter_name
            )
        return futures


    parser = argparse.ArgumentParser(
        "Funny File Filters",
        description="Use Funny File Filters on your image and look at the amazing result!"
    )
    parser.add_argument("input", help="The input image/folder")
    parser.add_argument("output", help="The output folder")
    parser.add_argument(
        "-f", "--filters", help="The filters to use, comma-separated. If unspecified, all will be used."
    )
    parser.add_argument("-t", "--threads", type=int, default=10, help="The number of max threads to use. Default is 10")
    args = parser.parse_args()


    input_path = path_relative_or_absolute(args.input)
    output_path = path_relative_or_absolute(args.output)
    max_threads = args.threads

    print(f"Input Folder/File: {input_path}")
    print(f"Output Folder: {output_path}")

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

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {}
        thread_count = 0

        if input_path.is_dir():
            for image_path in input_path.iterdir():
                result = submit_actions_for_single_file(
                    executor, filters_to_apply, image_path, output_path
                )
                futures[input_path] = result
                thread_count += len(result)
        elif input_path.is_file():
            result = submit_actions_for_single_file(
                executor, filters_to_apply, input_path, output_path
            )
            futures[input_path] = result
            thread_count += len(result)

        print(f"Threads ({thread_count} in total) are in the queue")
        print("Waiting for threads...")

        print()

        for i_file, (image_path, futures_for_image) in enumerate(futures.items(), 1):
            for i, future in enumerate(concurrent.futures.as_completed(futures_for_image.values()), 1):
                future_name = future.result()
                if future_name is not None:
                    print(f"Thread {i}/{len(futures)} ({future_name}) for file {i_file}({image_path}) is done!")
                else:
                    print(f"Thread {i}/{len(futures)} for file {i_file}({image_path}) is done!")

        print("All threads are done!")
        print(
            f"To see the result of Funny File Filters, open the generated images in the output folder ({output_path})"
        )


if __name__ == '__main__':
    main()
