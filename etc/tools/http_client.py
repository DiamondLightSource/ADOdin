#!/bin/env dls-python

from pkg_resources import require
require("requests")
import requests

import sys
import json
from argparse import ArgumentParser


def print_response(response, debug=False):
    if debug:
        print('HTTP/1.1 {status_code}\n{headers}\n\n{body}'.format(
            status_code=response.status_code,
            headers='\n'.join('{}: {}'.format(k, v) for k, v in response.headers.items()),
            body=response.content,
        ))
    else:
        print(json.dumps(
            parse_response(response),
            sort_keys=True, indent=4, separators=(",", ": ")
        ))


def parse_response(response):
    return json.loads(response.content)


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
        if "*/" in path:
            root, target = path.split("*/")
            response = requests.get(root)
            response_list = parse_response(response)["value"]
            for instance in response_list:
                for key, node in instance.items():
                    if not isinstance(node, dict) or target not in node.keys():
                        del instance[key]
                    else:
                        instance[key] = dict((k, v) for k, v in node.items() if k == target)
                response._content = json.dumps(response_list)
        else:
            response = requests.get(path)

    print_response(response, args.debug)


if __name__ == "__main__":
    sys.exit(main())
