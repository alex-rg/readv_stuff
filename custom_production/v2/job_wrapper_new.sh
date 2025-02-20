#!/bin/bash

source /cvmfs/lhcb.cern.ch/group_login.sh

mkdir ./repo
cd ./repo
git clone 'https://github.com/alex-rg/readv_stuff' .
cd patch_tests
echo "Starting"
date;
hostname;
#export XRD_LOGLEVEL=Dump
python3 readv_only_test.py -d "root://xrootd.echo.stfc.ac.uk:1094/lhcb:accounting/lhcb/dump_20240506?cephObjectSize=$((4*1024*1024))&cephStripeUnit=$((4*1024*1024))" -n 1000 -S "$((128*1024*1024))" -C 1024 -t random -N 1000

ret="$?"
echo "Finished $ret"
date;
exit "$ret"
