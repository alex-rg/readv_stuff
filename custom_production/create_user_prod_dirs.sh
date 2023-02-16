#!/bin/bash

dir=${1:-.}
out_dir=${2:-./output_dir}
script=${3:-./script.py}
cdir=`dirname $0`
count=0
for file in `find $dir -regextype egrep -regex '.*/[0-9]+$' -type f`; do
  job_dir="${out_dir}/${count}"
  mkdir "${job_dir}"
  ${cdir}/create_prodfiles.py -t user -l "root://xrootd.echo.stfc.ac.uk/lhcb:prod" -j "$file" -s "summary.xml" -o "${job_dir}/data.py"
  cp "$script" ${job_dir}/script.py
  count=$((count + 1))
done
