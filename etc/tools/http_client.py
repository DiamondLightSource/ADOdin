#!/bin/env dls-python

from pkg_resources import require
require("requests")
import requests

import sys
from argparse import ArgumentParser


def print_response(res, debug=False):
    if debug:
        print('HTTP/1.1 {status_code}\n{headers}\n\n{body}'.format(
            status_code=res.status_code,
            headers='\n'.join('{}: {}'.format(k, v) for k, v in res.headers.items()),
            body=res.content,
        ))
    else:
        print(res.content)


def main():
    parser = ArgumentParser("Send a request to an HTTP server")
    parser.add_argument("address", type=str, default=None, help="<URL>:<Port> for server")
    parser.add_argument("uri", type=str, default=None, help="URI of parameter")
    parser.add_argument("value", type=str, default=None, nargs="?", help="Value to PUT")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Print full response")
    args = parser.parse_args()

    path = "http://{}/api/0.1/{}".format(args.address, args.uri)
    if args.value is not None:
        response = requests.put(path, args.value)
    else:
        response = requests.get(path)

    print_response(response, args.debug)


if __name__ == "__main__":
    sys.exit(main())
