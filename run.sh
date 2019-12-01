#!/bin/bash

rm -rf dataset
rm -rf harvest


# https://www.worldatlas.com/aatlas/ctycodes.htm
countries="us,es,de,at,fr,cz,it,ae,mv,mt,hu,nl,me,hr,cy"

./pyapplicant.py --indeed --search search.txt --country $countries &&
./email_harvester.py &&

mkdir harvest
mv harvest.txt ./harvest/$countries.txt &&
echo 'OK' 
