# Imap inbox cleaner

# Fetch emails from your inbox

This fetches the headers of all unread emails in your inbox. Analysis can be performed on these headers later to see which emails are clogging up your inbox.

#### Usage

`python fetch.py imap_host username password`

*If you have a lot of unread emails in your inbox, then you can run this in the background by adding an '&' at the end of the command above. E.g.*

`python fetch.py imap_host username password &`

*This will produce a data.json file which will be used later*

*To see the progress of the fetch command you can periodically check the fetch log*

*The speed of fetching emails will depend on the specs of your machine, for me the script takes approximately 60 millisecond per unread email*

# Analyse emails

This analyses the headers you fetched earlier and gives you a breakdown of which emails are clogging up your inbox. 

#### Usage

`python analyse.py data.json`

#### Example output

You have 713 unread emails from 164 unique senders:

Last received &ensp;&ensp; Unread &ensp;&ensp; Address

26 Dec 2017 &ensp;&ensp;&ensp; 89 &ensp;&ensp;&ensp;&ensp;&ensp;&ensp; newsletter@indiegogo.com

24 Dec 2017 &ensp;&ensp;&ensp; 39 &ensp;&ensp;&ensp;&ensp;&ensp;&ensp; offers@topcashback.co.uk

27 Dec 2017 &ensp;&ensp;&ensp; 28 &ensp;&ensp;&ensp;&ensp;&ensp;&ensp; messages-noreply@linkedin.com

...

You have 713 unread emails from 139 unique domains:

Unread &ensp; Domain

92 &ensp;&ensp;&ensp;&ensp;&ensp; indiegogo.com (2 addresses)

66 &ensp;&ensp;&ensp;&ensp;&ensp; linkedin.com (6 addresses)

39 &ensp;&ensp;&ensp;&ensp;&ensp; topcashback.co.uk (1 address)

27 &ensp;&ensp;&ensp;&ensp;&ensp; mail.picturehouses.co.uk (1 address)

...

# Clean your inbox

Now you can define a set of commands to clean your inbox. Commands include deleting emails and marking them as read. You can match email addresses as exact string matches, match the domain of the email address, or using regex.

#### Usage

*To perform a dry run, run the following command, this will not make any changes*

`python clean.py data.json instructions_path`

*To go ahead and make the changes run the following command*

`python clean.py data.json instructions_path uid_validity imap_host username password`

*where the uid_validity is the same one from the fetch log file*

#### Example instructions file

*surround regex with quotation marks*

```
r indiegogo.com
d coffee.machine@companeo-news.co.uk
r ".*@.*monzo.*"
```

#### Terminal based program to build instructions

To rapidly go through your emails and build a list of instructions to perform, simply run:

`python build_instructions.py data.json`

This will show you the last 10 emails you have received from each domain, and you can type in the instruction you wish to perform on the emails, it will then move on to the next domain, etc. You can type 'f' and then enter at any time to finish. As you go through your emails the program will keep track of and display how many emails you have currently processed. 
