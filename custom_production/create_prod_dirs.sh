#!/bin/bash

dir=${1:-.}
out_dir=${2:-./output_dir}
cdir=`dirname $0`
count=0
for file in `find $dir -regextype egrep -regex '.*/[0-9]+$' -type f`; do
  job_dir="${out_dir}/${count}"
  mkdir "${job_dir}"
  ${cdir}/create_prodfiles.py -p "${cdir}/prod_conf.json" -l "root://xrootd.echo.stfc.ac.uk:1095/lhcb:prod" -j "$file" -s "summary.xml" -o "${job_dir}/prod_conf.json"
  count=$((count + 1))
done
