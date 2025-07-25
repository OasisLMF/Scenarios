#!/bin/bash

xargs -a models.txt -I {} aws s3 sync ./{} s3://oasislmf-scenarios/{} \
  --exclude '*runs/*'
