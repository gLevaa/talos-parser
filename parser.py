import sys
import json
from pprint import pprint

import talos_parser

def main():
    try:
        f = open('page.json')
        data = json.load(f)
    except:
        print("page.json not found, or invalid JSON structure.")

    if talos_parser.is_source(data):
        parser = talos_parser.SourceParser(data, None, sys.argv[1])
        parser.parse()

        pprint(parser.get_parsed())
    else:
        parser = talos_parser.PostParser(data)
        parser.parse()

        pprint(parser.get_parsed())

    f.close()

if __name__ == "__main__":
    main()