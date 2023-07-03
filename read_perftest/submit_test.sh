#!/bin/bash

rm -rf /pool/xcache/lhcb*
systemctl restart xrootd-proxy
sleep 190
docker run --network ralworker -v /cvmfs/lhcb.cern.ch:/cvmfs/lhcb.cern.ch -v /lhcb_job:/lhcb_job --rm d63b97cdac91 /bin/bash /lhcb_job/repo/read_perftest/test_reads.sh "$1"
