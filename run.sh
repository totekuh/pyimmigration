#!/bin/bash

rm -rf dataset

# https://www.worldatlas.com/aatlas/ctycodes.htm
countries="ca"
sender_address='ninja@virtualsquad'
subject='Job Application'
attach='cv.pdf'
openning_letter='text.txt'


./pyapplicant.py --indeed --search search.txt --country $countries &&
./email_harvester.py &&

emails=$countries'-emails.txt'
mv harvest.txt $emails &&

echo 'You can start a massive email delivery by running the following command:"'

echo "./smtp_massive_delivery.py --target "$emails" --file "$attach" --sender "$sender_address" --subject "$subject" --text "$openning_letter" --used-emails 'used-"$emails
