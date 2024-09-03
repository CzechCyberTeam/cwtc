#!/bin/bash

generate_id() {
    # $1 = len
    tr -dc "0-9A-Za-z" </dev/urandom 2>/dev/null | head -c "$1"
}

popcount() {
    # $1 = 8bit num
    echo -n $((
          (($1 >> 7) & 1)
        + (($1 >> 6) & 1)
        + (($1 >> 5) & 1)
        + (($1 >> 4) & 1)
        + (($1 >> 3) & 1)
        + (($1 >> 2) & 1)
        + (($1 >> 1) & 1)
        + (($1 >> 0) & 1)
    ))
}

ascii2int() {
    while IFS= read -n 1 -r -s -d "" x; do
        case "$x" in
            '') echo -n "0 ";;
            *) printf "%d " "'$x";;
        esac
    done
}

hex2int() {
    while IFS= read -n 2 -r -s -d "" x; do
        printf "%d " "0x$x";
    done
}

print_ascii() {
    # $1 = ascii code
    printf "\x$(printf "%x" "$1")"
}

declare -A Phonetic
Phonetic=(
    [_A]="Alfa"    [_B]="Bravo"  [_C]="Charlie" [_D]="Delta"    [_E]="Echo"
    [_F]="Foxtrot" [_G]="Golf"   [_H]="Hotel"   [_I]="India"    [_J]="Juliett"
    [_K]="Kilo"    [_L]="Lima"   [_M]="Mike"    [_N]="November" [_O]="Oscar"
    [_P]="Papa"    [_Q]="Quebec" [_R]="Romeo"   [_S]="Sierra"   [_T]="Tango"
    [_U]="Uniform" [_V]="Victor" [_W]="Whiskey" [_X]="Xray"     [_Y]="Yankee"
    [_Z]="Zulu"
    [_0]="Zero" [_1]="One" [_2]="Two"   [_3]="Three" [_4]="Four"
    [_5]="Five" [_6]="Six" [_7]="Seven" [_8]="Eight" [_9]="Nine"
)
