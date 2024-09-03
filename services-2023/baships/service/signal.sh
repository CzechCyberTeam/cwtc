#!/bin/bash

source ./ship.sh
source ./utility.sh

signal.block_encode() {
    # $1 = 1. byte
    # $2 = 2. byte
    # $3 = 3. byte
    # $4 = 4. byte
    # $5 = 5. byte
    # $6 = 6. byte
    # $7 = 7. byte
    # $8 = 8. byte
    # $9 = mod byte
    printf "%02x%02x%02x%02x%02x%02x%02x%02x%02x" \
        $(( $1 ^ ($9 & (1 << 7)) )) \
        $(( $2 ^ ($9 & (1 << 6)) )) \
        $(( $3 ^ ($9 & (1 << 5)) )) \
        $(( $4 ^ ($9 & (1 << 4)) )) \
        $((
              (( $(popcount $1) & 1) << 7)
            | (( $(popcount $2) & 1) << 6)
            | (( $(popcount $3) & 1) << 5)
            | (( $(popcount $4) & 1) << 4)
            | (( $(popcount $5) & 1) << 3)
            | (( $(popcount $6) & 1) << 2)
            | (( $(popcount $7) & 1) << 1)
            | (( $(popcount $8) & 1) << 0)
        )) \
        $(( $5 ^ ($9 & (1 << 3)) )) \
        $(( $6 ^ ($9 & (1 << 2)) )) \
        $(( $7 ^ ($9 & (1 << 1)) )) \
        $(( $8 ^ ($9 & (1 << 0)) ))
}

signal.buffered_int_encoder() {
    # stdin = data
    # $1 = mod
    buffer=""
    buffLen=0
    modOff=0
    while read -r -s -d " " x; do
        buffer+="$x "
        ((buffLen++))
        if [[ "$buffLen" == 8 ]]; then
            signal.block_encode $buffer "$(echo -n "${1:$modOff:1}" | ascii2int)"
            buffer=""
            buffLen=0
            ((modOff++))
            if [[ "$modOff" == "${#1}" ]]; then
                modOff=0
            fi
        fi
    done

    if [[ "$buffLen" != 0 ]]; then
        for (( ; buffLen < 8; buffLen++ )); do
            buffer+="32 "
        done
        signal.block_encode $buffer "$(echo -n "${1:$modOff:1}" | ascii2int)"
    fi
}

signal.encode() {
    # stdin = data
    # $1 = mod
    ascii2int | signal.buffered_int_encoder "$1"
}

signal.block_decode() {
    # $1 = 1. byte
    # $2 = 2. byte
    # $3 = 3. byte
    # $4 = 4. byte
    # $5 = 5. byte
    # $6 = 6. byte
    # $7 = 7. byte
    # $8 = 8. byte
    # $9 = 9. byte

    print_ascii "$(( $1 ^ (((($5 >> 7) ^ $(popcount $1)) & 1) << 7) ))"
    print_ascii "$(( $2 ^ (((($5 >> 6) ^ $(popcount $2)) & 1) << 6) ))"
    print_ascii "$(( $3 ^ (((($5 >> 5) ^ $(popcount $3)) & 1) << 5) ))"
    print_ascii "$(( $4 ^ (((($5 >> 4) ^ $(popcount $4)) & 1) << 4) ))"
    print_ascii "$(( $6 ^ (((($5 >> 3) ^ $(popcount $6)) & 1) << 3) ))"
    print_ascii "$(( $7 ^ (((($5 >> 2) ^ $(popcount $7)) & 1) << 2) ))"
    print_ascii "$(( $8 ^ (((($5 >> 1) ^ $(popcount $8)) & 1) << 1) ))"
    print_ascii "$(( $9 ^ (((($5 >> 0) ^ $(popcount $9)) & 1) << 0) ))"
}

signal.buffered_int_decoder() {
    # stdin = data
    buffer=""
    buffLen=0
    while read -r -s -d " " x; do
        buffer+="$x "
        ((buffLen++))
        if [[ "$buffLen" == 9 ]]; then
            signal.block_decode $buffer
            buffer=""
            buffLen=0
        fi
    done
}

signal.decode() {
    # stdin = data
    hex2int | signal.buffered_int_decoder
}

signal.generate_signature_id() {
    echo -n "$(generate_id $(( $RANDOM % 2 + 3 ))) $(generate_id 2).$(generate_id $(( $RANDOM % 3 + 1 )))/$(( $RANDOM % 2 + 1 ))"
}

signal.generate_signature_data() {
    head -c "$(( $RANDOM % 80 + 30 ))" </dev/urandom | base64 -w 0
}

signal.gather() {
    # $1 = source X
    # $2 = source Y
    # $3 = count
    echo "%Interference%"
    for x in "data/radar/${1}_${2}/"*; do
        ship.load other "$(basename "$x")"
        echo "${other[id]}\$${other[name]}"
    done
    echo "%Signals%"
    id="$(signal.generate_signature_id)"
    for (( x = 0; x < $3; x++ )); do
        sleep "0.$(( $RANDOM % 3 ))"
        echo "!$x!$id:$(signal.generate_signature_data)"
        if (( $RANDOM % 2 == 0)); then
            id="$(signal.generate_signature_id)"
        fi
    done
    echo "%End%"
}

signal.listen() {
    # $1 = source X
    # $2 = source Y
    # $3 = count
    # $4 = modulation
    signal.gather "$1" "$2" "$3" | signal.encode "$4"
}
