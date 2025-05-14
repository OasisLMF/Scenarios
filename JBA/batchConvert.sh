#!/bin/bash

printf "Batch footprint conversion started.\n"

if [ "$#" -ne 1 ]; then
  printf "Usage: $0 <configpath>"
  exit 1
fi

if [ ${1: -1} == '/' ]; then
  configpath="$1*"
else
  configpath="$1/*"
fi

for file in $configpath
do
  printf "Running config: $file \n"
  python FootprintConversionNumpy.py -c $file
  printf "\n"
done
