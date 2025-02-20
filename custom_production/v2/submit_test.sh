#!/bin/bash

#rm -rf /pool/xcache/lhcb*
#systemctl restart xrootd-proxy
#sleep 30
docker run -d \
    --network ralworker \
    -v "/cvmfs:/cvmfs:shared" \
    -v "/lhcb_job:/lhcb_job" \
    --name "jf_rate" \
    c80d53135be5 \
    /bin/bash -c 'echo "172.28.1.1    xrootd.echo.stfc.ac.uk" >> /etc/hosts && su --login lhcb001 -c "/bin/bash /lhcb_job/repo/custom_production/v2/do_run.sh "'"$1" &

while /bin/true; do
    sleep 10
    docker ps | grep -q 'jf_rate'
    [ "$?" -eq 0 ] || break
done
