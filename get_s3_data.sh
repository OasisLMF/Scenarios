#!/bin/bash

xargs -a large_files.txt -I {} aws s3 cp s3://oasislmf-scenarios/{} ./{}
