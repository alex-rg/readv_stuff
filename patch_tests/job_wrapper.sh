#!/bin/bash

#Grid job to reproduce "File name too long" error

echo "HOST: `hostname`"

source /cvmfs/lhcb.cern.ch/group_login.sh

#Copy file list -- just some random files with decent (approx 4GB each) size
lb-dirac gfal-copy https://webdav.echo.stfc.ac.uk:1094/lhcb:user/lhcb/user/a/arogovsk/readv_stuff/listOfRandomRALFiles5 ./listOfRandomRALFiles

for i in {1..6}; do
   python ./readv_only_test.py -t border -u `shuf -n 1 ./listOfRandomRALFiles` -s &
done

job_ids=`jobs | grep -o "^\[[0-9]\+\]" | tr -d '[]'`
wait `for i in $job_ids; do echo -n "%${i} "; done`
rm listOfRandomRALFiles
