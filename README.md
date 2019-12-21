# pyimmigration
</br>Python scripts to discover and collect a dataset of jobs applications. 

</br></br> <h2>STEP 1 - Finding job applications</h2>
<h3>A valid Indeed API-key is required to use the script.</h3>
</br>Use pyapplicant.py script to iterate through Indeed.com REST API and collect a dataset with job applications.
</br>The script has a few options to help you filter your results. 
</br>Use --help argument to see all of them.
<img src='https://i.imgur.com/Bi9gRuB.jpg'>

</br></br> <h2>STEP 2 - EMAIL HARVESTING</h2>
</br>Use email_harvester.py script to iterate through the collected dataset and attempt to scrape emails from a number of stored web-sites. This is the slowest step, as the script visits every web-site and every link in order to discover emails.
<img src='https://i.imgur.com/4ReutHf.jpg'>
<img src='https://i.imgur.com/bD4k26U.png'>

</br></br> <h2>STEP 3 - MASSIVE EMAIL DELIVERY</h2>
</br>Use massive_delivery.py script to perform a massive email delivery to the scraped email addresses. You have to give an smtp relay to use.

