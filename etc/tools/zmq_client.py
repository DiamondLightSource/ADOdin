#!/bin/env dls-python

from pkg_resources import require
require("pyzmq")
import zmq

import json
from argparse import ArgumentParser


def main():
    parser = ArgumentParser("Send a ZMQ message")
    parser.add_argument("address", type=str, default=None, help="<IP>:<Port> for server")
    # parser.add_argument("parameter", type=str, default=None, help="Path of parameter")
    # parser.add_argument("value", type=str, default=None, nargs="?", help="Value to set")
    args = parser.parse_args()

    context = zmq.Context()
    control_socket = context.socket(zmq.DEALER)
    control_socket.connect("tcp://{}".format(args.address))

    # params = {}
    # if args.value is not None:
    #     params["value"] = args.value

    message_template = \
        "{{\"msg_type\": \"cmd\"," \
        "\"id\": 1," \
        "\"msg_val\": \"{}\"," \
        "\"params\": {{}}," \
        "\"timestamp\": \"2017-09-16T14:17:58.440432\"}}"

    control_socket.send(message_template.format("status"))
    message = control_socket.recv_json()
    print("Status: {}".format(
        json.dumps(message, sort_keys=True, indent=4, separators=(",", ": ")))
    )

    control_socket.send(message_template.format("request_configuration"))
    message = control_socket.recv_json()
    print("Configuration: {}".format(
        json.dumps(message, sort_keys=True, indent=4, separators=(",", ": ")))
    )

    control_socket.close(linger=1000)
    context.term()


if __name__ == "__main__":
    main()
