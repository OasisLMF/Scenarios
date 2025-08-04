#!/bin/bash

xargs -a large_files.txt -I {} aws s3 cp --no-sign-request s3://oasislmf-scenarios/{} ./{}
