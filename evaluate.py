"""Score every case in ./cases against its answer key. Same as: python -m detective evaluate"""

import sys

from detective.cli import main

if __name__ == "__main__":
    sys.exit(main(["evaluate", *sys.argv[1:]]))
