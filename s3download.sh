#!/bin/bash

# Bash script to download the entire repo from s3, useful for deployment

readarray -t modelpaths < models.txt
readarray -t ignoredfiles < ignored_files.txt

echo "${modelpaths[@]}"
echo "${ignoredfiles[@]}"
# xargs -a models.txt -I {} aws s3 cp --no-sign-request s3://oasislmf-scenarios/{} ./{}
BASERUNCOMMAND=(aws s3 sync )
IGNOREDCOMMAND=()
for p in "${ignoredfiles[@]}"
do
  IGNOREDCOMMAND+=(--exclude $p)
done

for p in "${modelpaths[@]}"
do
  echo "Copying ${p}"
  RUNCOMMAND=("${BASERUNCOMMAND[@]}" "s3://oasislmf-scenarios/$p" "./$p" "${IGNOREDCOMMAND[@]}")
  "${RUNCOMMAND[@]}"
done
