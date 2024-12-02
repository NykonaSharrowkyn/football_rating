import football_rating_utility

import argparse
import os

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog='many files launcher',
        description='Utility to launch many files in sequence'
    )
    parser.add_argument('path', help='path template without indices')
    parser.add_argument('count', type=int, help='')
    return parser.parse_args()

def main(path: str, count: int):
    name, ext = os.path.splitext(path)
    for i in range(count):
        football_rating_utility.main(f'{name}_{i+1}{ext}')

if __name__ == '__main__':
    args = parse_arguments()
    main(**vars(args))