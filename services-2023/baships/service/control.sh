#!/bin/bash
# $1 = ship ID

export LC_ALL=C

source ./input.sh
source ./map.sh
source ./report.sh
source ./ship.sh
source ./signal.sh

ship.load ship "$1"

print_status() {
    # $1 = prefix
    printf "${1}Operational:  %d\n" $((! ${ship[destroyed]}))
    printf "${1}Location:     x=%d y=%d\n" "${ship[x]}" "${ship[y]}"
}

wait() {
    # $1 = count
    for (( x = 0; x < "$1"; x++ )); do
        echo -n "."
        sleep 0.5
    done
    echo
}

echo "Connecting to: ${ship[id]}"
echo "Received name: ${ship[name]}"
sleep 0.5
print_status
sleep 0.3

if [[ "${ship[destroyed]}" == 1 ]]; then
    echo "Ship not operational, connection cannot be made"
    exit 0
fi

echo "Connection established..."
sleep 0.2
echo "Control interface active, ship is accepting commands:"

while input=$(read_line); do
    first="${input%% *}"
    case "$first" in
        "adrift")
            wait 3
            if [[ "${ship[x]}" == 0 && "${ship[y]}" == 0 ]]; then
                adrift=$(map.adrift)
                x="${adrift% *}"
                y="${adrift#* }"
                map.move_ship "${ship[id]}" "${ship[x]}" "${ship[y]}" "$x" "$y"
                ship[x]=$x
                ship[y]=$y
            else
                map.move_ship "${ship[id]}" "${ship[x]}" "${ship[y]}" 0 0
                ship[x]=0
                ship[y]=0
            fi
        ;;
        "disconnect")
            break
        ;;
        "find")
            if ! has_n_words "$input" 2; then
                echo "find <source>"
                continue
            fi
            report.find "${input#find }"
        ;;
        "move")
            if ! has_n_words "$input" 3; then
                echo "move <x> <y>"
                continue
            fi
            sleep 0.3
            if ! x=$(process_int $(echo -n "$input" | cut -d " " -f 2)); then
                echo "Relocation failed"
                continue
            fi
            if ! y=$(process_int $(echo -n "$input" | cut -d " " -f 3)); then
                echo "Relocation failed"
                continue
            fi
            if ! map.try_move_ship "${ship[id]}" "${ship[x]}" "${ship[y]}" "$x" "$y"; then
                echo "Relocation failed"
                continue
            fi
            ship[x]=$x
            ship[y]=$y
            echo "Ship relocated"
        ;;
        "radio")
            if ! has_n_words "$input" 3; then
                echo "radio <count> <modulation>"
                continue
            fi
            if [[ "${ship[x]}" == 0 && "${ship[y]}" == 0 ]]; then
                echo "Environment too noisy"
                continue
            fi
            if ! count=$(process_int "$(echo -n "$input" | cut -d " " -f 2)"); then
                continue
            fi
            echo "Listening for signal signatures ($count)..."
            signal.listen "${ship[x]}" "${ship[y]}" "$count" "${input#radio * }"
            echo ""
        ;;
        "rename")
            if ! has_n_words "$input" 2; then
                echo "rename <name>"
                continue
            fi
            ship[name]="${input#rename }"
            ship.save ship
            echo "Ship renamed"
        ;;
        "report")
            if ! has_n_words "$input" 2; then
                echo "report <signal data>"
                continue
            fi
            echo -n "${input#report }"| signal.decode | report.from_signal_data
        ;;
        "retrieve")
            if ! has_n_words "$input" 3; then
                echo "retrieve <pass> <ID>"
                continue
            fi
            report.show "$(echo -n "$input" | cut -d " " -f 2)" "${input#retrieve * }"
        ;;
        "scuttle")
            ship[destroyed]=1
            wait 5
            echo "Connection lost, last info:"
            print_status "    "
            break
        ;;
        "status")
            echo "Current status:"
            print_status "    "
        ;;
    esac
done

ship.save ship
