#!/bin/bash
docker run -d \
    -v  "/etc/glexec.conf:/etc/glexec.conf:ro" \
    -v "/etc/lcmaps:/etc/lcmaps:ro" \
    -v "/etc/lcas:/etc/lcas:ro" \
    -v "/lhcb_job:/lhcb_job" \
    -v "/etc/grid-security:/etc/grid-security:ro" \
    -v  "/etc/profile.d/grid-env.sh:/etc/profile.d/grid-env.sh:ro" \
    -v "/cvmfs:/cvmfs:shared" \
    -e "LOG_DIRECTORY=/lhcb_job/${2}" \
    --network ralworker \
    --name test_job_${1} \
    b97af4dd7269 \
    /bin/bash -c 'echo "172.28.1.1    xrootd.echo.stfc.ac.uk" >> /etc/hosts && su -c "/bin/bash -c \"cd /lhcb_job/user_jobs/'"${1}"' && ../../repo/custom_production/start_user_job.sh\"" --login lhcb001'
