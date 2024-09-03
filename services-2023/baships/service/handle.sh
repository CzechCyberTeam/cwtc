#!/bin/bash
source ./user.sh

echo "User:"
read username
echo "Password:"
read pass

username=$(echo -n "$username" | tr -d /)
pass_hash=$(echo -n "$pass" | sha256sum | cut -d " " -f 1)

if [[ -f "data/users/$username" ]]; then
    if ! user.check_pass "$username" "$pass_hash"; then
        echo "Authetication failed"
        exit 0
    fi
else
    if [[ -e "data/users/$username" ]] || ! user.register "$username" "$pass_hash"; then
        echo "Authetication failed"
        exit 0
    fi
fi

user.load "$username"
echo "Succesfuly autheticated, control session created"
sleep 0.5
./control.sh "${user[shipID]}"
user.save
echo "Session closed"
