import sys

from composition import build_service, database_path, get_connection
from ui import cli


def main(argv=None) -> int:
    connection = get_connection(database_path())
    try:
        return cli.run(build_service(connection), argv)
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
