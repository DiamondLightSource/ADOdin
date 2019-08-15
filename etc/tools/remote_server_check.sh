#!/bin/bash
# Script to run odin-data server checks on remote servers

echo Running Remote Server check

if [ "$1" == "" ]; then
  echo "  No servers specified"
  echo "  Usage: remote_server_check SERVER1 [SERVER2] [...]"
  exit
fi

for server in "$@"
do
  echo Checking $server
  ssh $server 'bash -s' < ./server_check.sh
  echo ""
done
