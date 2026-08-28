#!/bin/bash

tar -czvf scenarios.tar.gz --exclude 'runs' \
  --exclude '*log' --exclude '*.zip' -T ./scenarios_models.txt
