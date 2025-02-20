#!/bin/bash
JOBS="$1"
job="$JOBS"

cd /lhcb_job/myjob
ls /cvmfs/lhcb.cern.ch
source /cvmfs/lhcb.cern.ch/group_login.sh
#source /cvmfs/sft.cern.ch/lcg/views/LCG_103/x86_64-centos7-gcc9-opt/setup.sh
export X509_USER_PROXY=/lhcb_job/proxy.pem
#export XRD_LOGLEVEL=Dump

yum install -y time

while [ "$job" -gt 0 ]; do
    /usr/bin/time -o "/lhcb_job/myjob/out_${job}/times.txt" -f "CPU user: %U ; CPU System: %S; Wall: %E\n%P"  /bin/bash -c "cd /lhcb_job/myjob/out_${job} ; /lhcb_job/myjob/job_wrapper_new.sh > /lhcb_job/myjob/out_${job}/std.out 2>/lhcb_job/myjob/out_${job}/std.err" &
    /#usr/bin/timeout 7200 lb-run --siteroot=/cvmfs/lhcb.cern.ch/lib -c x86_64_v2-centos7-gcc11-opt --path-to-project /lhcb_job/myjob/DaVinciDev_46.4 gaudirun.py script.py "out_${job}/data.py" > "out_${job}/std.out"  2> "out_${job}/std.err" &
    job=$((job - 1))
done

while /bin/true; do
  file=`shuf -n 1 /lhcb_job/dump.lhcb`
  xrdcp -f "root://xrootd.echo.stfc.ac.uk:1094/lhcb:${file}" ./output.file
done &

proc=`jobs | grep -v xrdcp | sed -e 's/^\[\([0-9]\+\)\].*/\1/'`
for jid in $proc; do
   wait "%$jid";
done

kill -TERM $(jobs -p)

successes=`grep 'INFO Application Manager Terminated successfully' /lhcb_job/myjob/out_*/std.out | wc -l`
echo "${JOBS} ${successes}" >>  /lhcb_job/myjob/job_failure_stats
