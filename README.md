# Fuel Price Notifier
Get the current fuel price reported at the German [MTS-K system](http://www.bundeskartellamt.de/DE/Wirtschaftsbereiche/Mineral%C3%B6l/MTS-Kraftstoffe/Verbraucher/verbraucher_node.html) and sent a mail notification when the price is very low.

This works by using the [benzinpreis-aktuell.de API](https://www.benzinpreis-aktuell.de/api2/).

# Setup

1) Clone this repository into a new folder. 

2) Add a new file called `config.py`, which looks like this:

```python
# -*- coding: utf-8 -*-

# Required settings
api_link_json=""
smtp_server = "smtp.gmail.com"
email_sender = ""
email_sender_password = ""
email_receiver_super = ""
email_receiver_diesel = ""

# Optional settings
alert_percentile = 20
days_for_percentile = 5
```


3) You have to register a new API account at https://www.benzinpreis-aktuell.de/api2/ and copy your individual JSON url into `api_link_json`

4) Create a new or exisiting email account and find out the address of the SMTP server. For gmail it is prefilled, which is way I would recommend it. 

5) Enter your sender address in `email_sender` and your sender adress password (Google account password) in `email_sender_password`

6) Enter the email you want to receive the notification at under `email_receiver_super` or `email_receiver_diesel` or both, depending on what type of fuel you want to be notified about.
