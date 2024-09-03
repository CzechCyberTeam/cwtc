#!/bin/bash

source ./ship.sh

mkdir -p data/users

user.register() {
    # $1 = user
    # $2 = hash
    echo "$2" > "data/users/$1"
    date +%s >> "data/users/$1"
    ship.new >> "data/users/$1"
}

user.check_pass() {
    # $1 = user
    # $2 = hash
    test "$2" = $(head -n 1 "data/users/$1")
}

user.load() {
    # $1 = user
    declare -Ag user
    user[dir]="data/users/$1"
    user[name]="$1"
    user[pass]=$(head -n 1 "${user[dir]}" | tail -n 1)
    user[last]=$(head -n 2 "${user[dir]}" | tail -n 1)
    user[shipID]=$(head -n 3 "${user[dir]}" | tail -n 1)
}

user.save() {
    cat <<EOF > "${user[dir]}"
${user[pass]}
$(date +%s)
${user[shipID]}
EOF
}

