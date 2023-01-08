#!/bin/bash
export XRD_LOGLEVEL="Dump"
DIR="${1:-x}"
if [ "$DIR" != "x" ] ; then
    LIST=${2:-../../listOfRandomRALFiles5}
    [ -d "$DIR" ] || mkdir "$DIR"
    for i in {1..64}; do
        ./readv_only_test.py -c -l "$LIST" -S $((42*1024*1024)) -N 1000 -n 128 2>&1 | tee >(../analyze/log2csv.py -o "${DIR}/data_${i}.csv" - ) | tail -n 1000 >> "${DIR}/last_output_${i}" &
    done
else
    echo "Specify log directory"
    exit 1
fi
