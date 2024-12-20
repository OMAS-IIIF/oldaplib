import argparse
import os
from pprint import pprint

import yaml


def main():
    parser = argparse.ArgumentParser(
        prog='listloader',
        description='Load a list of files from a YAML file',
    )
    parser.add_argument('filename')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-t', '--testonly', action='store_true')

    print(os.getcwd())
    args = parser.parse_args()
    with open(args.filename, 'r') as f:
        obj = yaml.safe_load(f)
        for listid, listdata in obj.items():
            print("List ID", listid)
            print("List label:", listdata['label'])
            print("List description:", listdata['description'])
            for nodeid, nodedata in listdata['nodes'].items():
                print("  Node ID", nodeid)

if __name__ == '__main__':
    main()