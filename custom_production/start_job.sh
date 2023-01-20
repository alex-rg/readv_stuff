#!/bin/bash

source /cvmfs/lhcb.cern.ch/group_login.sh
export X509_USER_PROXY=/lhcb_job/proxy.pem
export XRD_LOGLEVEL=Dump
mkfifo ./stderr_fifo
cat ./stderr_fifo | tee >( ../../../analyze/log2csv.py -o ./vector_times.csv -) >(../../../analyze/log2csv.py -o ./read_times.csv -r read - ) | tail -n 10000 > last_std.err &
lb-prod-run "prod_conf.json" --verbose 2> ./stderr_fifo
retcode="$?"
[ "$retcode" -eq 0 ] && rm ./stderr_fifo || exit "$retcode"
