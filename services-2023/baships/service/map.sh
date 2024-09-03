#!/bin/bash

mkdir -p data/radar

MAX_MOVE_DISTANCE=5
ADRIFT_MIN=300000
ADRIFT_MAX=1000000

map.distance() {
    # $1 = x0
    # $2 = y0
    # $3 = x1
    # $4 = y1
    awk -v "x0=$1" -v "y0=$2" -v "x1=$3" -v "y1=$4" 'BEGIN{print sqrt((x0-x1)^2+(y0-y1)^2)}'
}

map.is_valid() {
    # $1 = x0
    # $2 = y0
    # $3 = x1
    # $4 = y1
    distance=$(map.distance "$@" | cut -d "." -f 1)
    if (( "$distance" < "$MAX_MOVE_DISTANCE" )); then
        return 0
    else
        return 1
    fi
}

map.adrift() {
    # Random in awk is weird... It also behaves differently on e.g. ubuntu
    # and debian even though version of awk is same.
    awk -v "s=$(od -A n -l -N 8 /dev/urandom)" -v "min=$ADRIFT_MIN" -v "max=$ADRIFT_MAX" -f - <<EOF
BEGIN {
    srand(s)
    x=rand()*(max-min)+min
    y=rand()*(max-min)+min
    if (rand() > 0.5) x*=-1
    if (rand() > 0.5) y*=-1
    print int(x) " " int(y)
}
EOF
}

map.try_move_ship() {
    # $1 = Ship ID
    # $2 = From X
    # $3 = From Y
    # $4 = To X
    # $5 = To Y
    if ! map.is_valid "$2" "$3" "$4" "$5"; then
        return 1
    fi
    map.move_ship "$@"
}


map.move_ship() {
    # $1 = Ship ID
    # $2 = From X
    # $3 = From Y
    # $4 = To X
    # $5 = To Y
    rm "data/radar/${2}_${3}/$1" 2>/dev/null
    rm -d "data/radar/${2}_${3}" 2>/dev/null
    mkdir -p "data/radar/${4}_${5}" && ln "data/ships/$1" "data/radar/${4}_${5}/$1"
}

