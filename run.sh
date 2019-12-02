#!/bin/bash

rm -rf dataset

# https://www.worldatlas.com/aatlas/ctycodes.htm

# search jobs properties
query_file='search.txt'
countries="ca"
job_type='all'
days_since_published=10

./pyapplicant.py --indeed \
--search $query_file \
--country $countries \
--days $days_since_published \
--job-type $job_type &&

./email_harvester.py &&

emails=$countries'-emails.txt'
mv harvest.txt $emails &&

echo 'You can start a massive email delivery by running the following command:"'

# mailing properties here
sender_address='ninja@virtualsquad'
subject='Job Application'
attach='cv.pdf'
openning_letter='text.txt'

echo "./massive_delivery.py --target "$emails" --file "$attach" --sender "$sender_address" --subject "$subject" --text "$openning_letter" --used-emails 'used-"$emails
