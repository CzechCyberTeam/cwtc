#!/bin/sh

source signal.sh

mkdir -p data/reports/sources
mkdir -p data/reports/stored

report.from_signal_data() {
    # stdin = data
    declare -a signals
    section=""
    while read x; do
        if  [[ "%" == "${x:0:1}" ]]; then
            section=${x:1:-1}
            continue
        fi
        if [[ "$section" == "Interference" ]]; then
            continue
        fi
        if [[ "$section" == "Signals" ]]; then
            signals+=("${x#!*!}")
            continue
        fi
    done

    if [[ "$section" != "End" ]]; then
        echo "Malformed signal data"
        return 1
    fi

    cd "data/reports"
    declare -A sources
    for x in "${signals[@]}"; do
        id="${x%%:*}"
        data="${x#*:}"
        if [[ -v 'sources[$id]' ]]; then
            (( sources[$id]++ ))
        else
            sources[$id]=1
        fi
    done

    i="$(generate_id 17).$(generate_id 7).$(generate_id 3)_$(generate_id 2)"
    p=$(echo -n $i | sha256sum | cut -d " " -f 1 | xxd -ps -r | base64 | head -c 30)
    exec 3> "stored/$i"

    echo "$p" >&3
    echo "=== Report $i ===" >&3

    echo "Signature count by source:" >&3
    for x in "${!sources[@]}"; do
        echo "    > $x: ${sources[$x]}" >&3
        mkdir -p "$(dirname "sources/$x")"
        echo "$i" >> "sources/$x"
    done

    echo "Captured signatures:" >&3
    for x in "${signals[@]}"; do
        echo "    $x" >&3
    done

    echo "Cross report source references:" >&3
    for x in "${!sources[@]}"; do
        grep -H -m 1 -E "^    > ($x): [0-9]+\$" stored/* | awk -v "i=$i" '{sub(" +"," ");if(substr($0,8,32)!=i)print"    "substr($0,8)}' >&3
    done
    echo "=== Report end ===" >&3

    echo "Generated report: Key=$p ID=$i"
    cd - >/dev/null
}

report.find() {
    # $1 = source
    cd "data/reports/sources"
    file="$(realpath "$1")"
    file="$PWD/${file#"$PWD"}"
    if [[ -f "$file" ]]; then
        echo "Reports with this source signature:"
        cat "$file"
        echo "(Total $(cat "$file" | wc -l) reports)"
    else
        echo "Requested source signature was not captured"
    fi
    cd - >/dev/null
}

report.show() {
    # $1 = password
    # $2 = report ID
    cd "data/reports/stored"

    if [[ ! -f "$2" ]]; then
        echo "Report not found"
        cd - >/dev/null
        return 1
    fi

    if [[ "$1" != "$(cat "$2" | head -n 1)" ]]; then
        echo "Unauthorized for report access"
        cd - >/dev/null
        return 1
    fi
    
    echo "Successfully authorized for report access"
    tail -n +2 $2
    cd - >/dev/null
}
