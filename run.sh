#!/bin/bash

# https://www.worldatlas.com/aatlas/ctycodes.htm
countries="it,ae,mv,mt,hu,nl,me,hr,cy"

./pyapplicant.py --indeed --search search.txt --country $countries &&
./email_harvester.py &&
mv harvest.txt ./harvest/$countries.txt &&
echo 'OK' 
