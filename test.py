from pathlib import Path
from pprint import pprint
from typing import List, Tuple, Any


def partition_integers(tuples, groups):
    result = [[] for _ in range(groups)]
    for time_points, value in sorted(tuples, reverse=True):
        sums = [(i, sum(x[0])) for i, x in enumerate(result)]
        index_with_lowest_sum = min(sums, key=lambda x: x[1])[0]

        result[index_with_lowest_sum].append((time_points, value))

    return result

tuples: List[
    Tuple[
        int, Any
    ]
]
# def partition_integers(tuples, groups):
#     result = [[] for _ in range(groups)]
#     for value in sorted(tuples, reverse=True):
#         sums = [(i, sum(ints)) for i, ints in enumerate(result)]
#         index_with_lowest_sum = min(sums, key=lambda x: x[1])[0]
#
#         result[index_with_lowest_sum].append(value)
#
#     return result




def main():
    values = list(range(100_000))
    print("Start Calculating...")
    result = partition_integers(values, 30)
    pprint(result)
    print([sum(ints) for ints in result])


if __name__ == '__main__':
    from pathlib import Path

    CURRENT = Path(__file__).parent


    full_path = CURRENT / "input/minecraft/textures/block/bamboo_block.png"
    start_path = CURRENT / "input"

    relative_path = full_path.relative_to(start_path)
    print("Relative path using pathlib:", relative_path)


    print(list((CURRENT / "input").rglob("*")))
