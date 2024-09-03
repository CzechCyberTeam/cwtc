#!/bin/bash
cd service
cmd="socat TCP-LISTEN:9999,reuseaddr,fork,cool-write,keepalive,keepcnt=1,keepidle=3,keepintvl=3 EXEC:./handle.sh,nofork,cool-write"

print_help() {
    echo "$0 <TERMINAL|DAEMON>"
    echo -e "\tTERMINAL - Runs server in current terminal"
    echo -e "\tDAEMON   - Runs server in different process; you will need to use 'kill' command to stop it"
}

if [[ $# != 1 ]]; then
    print_help
    exit 1
fi

if [[ "${1^^}" == "TERMINAL" ]]; then
    echo "Starting server..."
    exec $cmd
elif [[ "${1^^}" == "DAEMON" ]]; then
    $cmd &
    disown
    echo "Server started"
else
    print_help
    exit 1
fi
