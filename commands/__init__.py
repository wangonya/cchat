import argparse
import pathlib


def path():
    return pathlib.Path(__file__).parent.absolute()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--output', action='store_true',
                        help="shows output")

    args = parser.parse_args()

    if args.output:
        print("This is some output")
