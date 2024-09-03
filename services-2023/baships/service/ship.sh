#!/bin/sh

source ./map.sh
source ./utility.sh

mkdir -p data/ships

ship.load() {
    # $1 = output var
    # $2 = ship ID

    file="data/ships/$2"

    declare -Ag $1
    eval "$1[file]=\$file"
    eval "$1[id]=\$2"
    eval "$1[destroyed]=\$(head -n 1 \"\$file\" | tail -n 1)"
    eval "$1[name]=\$(head -n 2 \"\$file\" | tail -n 1)"
    eval "$1[x]=\$(head -n 3 \"\$file\" | tail -n 1 | cut -d ' ' -f 1)"
    eval "$1[y]=\$(head -n 3 \"\$file\" | tail -n 1 | cut -d ' ' -f 2)"
}

ship.save() {
    # $1 = input var
    eval "$(cat <<EOF
cat <<EOF > "\${$1[file]}"
\${$1[destroyed]}
\${$1[name]}
\${$1[x]} \${$1[y]}
${$:+}EOF
EOF
)"
}

ship.new() {
    shipID=$(generate_id 32)
    shipName=""
    for x in {0..2}; do
        shipName="$shipName ${Phonetic["_$(echo -n ${shipID:$x:1} | tr 'a-z' 'A-Z')"]}"
    done
    cat <<EOF > "data/ships/$shipID"
0
Ship "${shipName:1}"
0 0
EOF
    map.move_ship $shipID 0 0 0 0
    echo -n $shipID
}
