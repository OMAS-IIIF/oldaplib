import sys
from argparse import ArgumentParser
from pathlib import Path

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.oldaplist_helpers import load_list_from_yaml, print_sublist
from oldaplib.src.project import Project


def load_list():
    parser = ArgumentParser(prog="load_list",
                            description="Loads YAML file with hierarchical list.")
    parser.add_argument("file", help="YAML file with hierarchical list")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show some informational output")
    parser.add_argument('-u', '--user', required=True, help="Username")
    parser.add_argument('-p', '--password', required=True, help="Password")
    parser.add_argument('--project', required=True, help="Project ID")
    #parser.add_argument('-h', '--help', help="Show help information")
    args = parser.parse_args()

    try:
        connection = Connection(server='http://localhost:7200',
                                repo="oldap",
                                userId=args.user,
                                credentials=args.password,
                                context_name="DEFAULT")
        project = Project.read(connection, args.project)
        path = Path(args.file)
        listnodes = load_list_from_yaml(con=connection,
                                        project=args.project,
                                        filepath=path)
        if args.verbose:
            listnode = listnodes[0]
            print_sublist(listnode.nodes)
    except OldapError as error:
        print(f'ERROR: {error}!', file=sys.stderr)
        exit(-1)
    except FileNotFoundError as error:
        print(f'ERROR: {error}!', file=sys.stderr)
        exit(-1)


if __name__ == '__main__':
    load_list()
