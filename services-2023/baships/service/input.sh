#!/bin/bash

read_line() {
    if ! read input; then
        return 1
    fi
    echo $input
}

process_int() {
    # $1 = input
    echo -n "$1" | grep -E -o -- '(-|\+)?[0-9]+'
}

has_n_words() {
    # $1 = input
    # $1 = target word count
    [[ -n "$(echo -n "$1" | cut -d " " -s -f "$2")" ]]
}
