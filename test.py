from pathlib import Path
from pprint import pprint


def partition_integers(tuples, groups):
    result = [[] for _ in range(groups)]
    for time_points, value in sorted(tuples, reverse=True):
        sums = [(i, sum(x[0])) for i, x in enumerate(result)]
        index_with_lowest_sum = min(sums, key=lambda x: x[1])[0]

        result[index_with_lowest_sum].append((time_points, value))

    return result

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
    CURRENT = Path(__file__).parent
    CURRENT_FILE = Path(__file__)

    print(CURRENT_FILE.relative_to(CURRENT_FILE))
