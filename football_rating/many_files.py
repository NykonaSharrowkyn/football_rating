import football_rating_utility

import argparse
import sys
import os

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog='many files launcher',
        description='Utility to launch many files in sequence'
    )
    parser.add_argument('path', help='path template without indices')
    parser.add_argument('count', type=int, help='')
    parser.add_argument('-s', '--storage', default='football-rating-test')
    return parser.parse_args()

def main(path: str, count: int, storage: str):
    name, ext = os.path.splitext(path)
    for i in range(count):
        football_rating_utility.update_rating(f'{name}_{i+1}{ext}', storage)

if __name__ == '__main__':
    args = parse_arguments()
    os.chdir(sys.path[0])
    main(**vars(args))