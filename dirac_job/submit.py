#!/usr/bin/env python3
import argparse

from DIRAC.Interfaces.API.Dirac import Dirac
from DIRAC.Interfaces.API.Job import Job

DEF_CPUTIME = 300
DEF_JOBNAME = "test_job"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--site', help="Site to run job on")
    parser.add_argument('-n', '--name', help="Job name. Default is {0}".format(DEF_JOBNAME), default=DEF_JOBNAME)
    parser.add_argument('-m', '--multiple', help="Submit multiple jobs with the same script. Value gives the number of jobs to submit", type=int, default=1)
    parser.add_argument('-c', '--cpu_time', help="CPU Time for the job. Default is {0}".format(DEF_CPUTIME), default=DEF_CPUTIME, type=int)
    parser.add_argument('executable', help="Script to run")
    return parser.parse_args()
    

if __name__ == '__main__':
    args = parse_args()
    j = Job()
    j.setCPUTime(args.cpu_time)
    j.setExecutable(args.executable)
    if args.site:
        j.setDestination(args.site)
    for i in range(args.multiple):
        if args.multiple > 1:
            jname = args.name + '_{0}'.format(i)
        else:
            jname = args.name
        j.setName(jname)

        dirac = Dirac()
        result = dirac.submitJob(j)
        if result['OK']:
            print(result['Value'])
        else:
            print('Failed to submit: ',result)
