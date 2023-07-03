#!/bin/bash

FILE_SIZE=$((1000*1000*1000))
FILE_BASE_URL="root://xrootd.echo.stfc.ac.uk/lhcb:user/lhcb/user/a/arogovsk/perftest_file"
JOBS="$1"

copy_file() {
  local url="$1" start_time end_time ret size
  start_time=`date "+%s"`
  xrdcp -f "$url" /dev/null 2>&1 # 2> "std_`basename ${url} | grep -o "[0-9]\+"`.err"
  ret="$?"
  end_time=`date "+%s"`
  echo "$((end_time - start_time))" "$ret"
  return "$ret"
}

echo "172.28.1.1      xrootd.echo.stfc.ac.uk" > /etc/hosts
source /cvmfs/lhcb.cern.ch/group_login.sh
export X509_USER_PROXY=/lhcb_job/proxy.pem
echo "JOBS $JOBS"
for i in `seq "$JOBS"`; do
  copy_file "${FILE_BASE_URL}${i}" &
done
wait
echo
