#!/bin/bash

xargs -a large_files_reduced.txt -I {} aws s3 --no-sign-request sync s3://oasislmf-scenarios/{} ./{}
