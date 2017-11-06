# -*- coding: utf-8 -*-
import requests
import json
import time
import sys
import sqlite3
import numpy as np
import smtplib
from config import smtp_server, api_link_json, email_sender, email_sender_password, email_receiver_super, \
    email_receiver_diesel, alert_percentile, days_for_percentile

# Open sqlite database
connection = sqlite3.connect("tanken.db")
cursor = connection.cursor()


def create_table():
    sql_command = """
    CREATE TABLE 'preis' ( 
    time INTEGER PRIMARY KEY, 
    price_super INTEGER, 
    price_diesel INTEGER 
    );"""
    cursor.execute(sql_command)


def insert_db(price_super, price_diesel):
    millis = int(round(time.time() * 1000))
    format_str = """INSERT INTO 'preis' (time, price_super, price_diesel)
    VALUES ("{time}", "{price_super}", "{price_diesel}");"""
    sql_command = format_str.format(time=millis, price_super=price_super, price_diesel=price_diesel)
    try:
        cursor.execute(sql_command)
        connection.commit()
    except Exception as e:
        if isinstance(e, sqlite3.OperationalError) and "no such table" in format(e):
            print("Table not created, doing it now. Next time it should work!")
            create_table()
            sys.exit(0)
        else:
            print("Error while inserting into db" + format(e))


def get_percentiles():
    millis = int(round(time.time() * 1000))
    # Nur die letzten 5 Tage berücksichtigen
    millis_days_ago = str(millis - (days_for_percentile * 24 * 60 * 60 * 1000))
    cursor.execute("SELECT price_super, price_diesel FROM preis WHERE time > " + millis_days_ago)

    super_prices = []
    diesel_prices = []
    results_db = cursor.fetchall()
    for line in results_db:
        super_prices.append(line[0])
        diesel_prices.append(line[1])
    # use numpy to generate a percentile
    super_percentile_value = np.percentile(np.array(super_prices), alert_percentile)
    diesel_percentile_value = np.percentile(np.array(diesel_prices), alert_percentile)
    return [super_percentile_value, diesel_percentile_value]


def send_mail(to, subject):
    if to == "" or to is None:
        return
    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(email_sender, email_sender_password)
    message = 'Subject: {}'.format(subject)
    server.sendmail(email_sender, to, message)
    server.quit()


def load_current_prices():
    r = requests.get(api_link_json)
    if r.status_code != 200:
        print("Aborting, bad status code with result: " + r.text)
        sys.exit(0)

    result = json.loads(r.text)
    current_price_super = int(float(result['stations'][0]['price_super']) * 100 - 0.9)
    current_price_diesel = int(float(result['stations'][0]['price_diesel']) * 100 - 0.9)

    return [current_price_super, current_price_diesel]


# Load current prices and store them into vars
price_array = load_current_prices()
price_super = price_array[0]
price_diesel = price_array[1]

# Insert the prices into the db
insert_db(price_super, price_diesel)

# Load the percentiles by fetching values from db
p_array = get_percentiles()
p_super = p_array[0]
p_diesel = p_array[1]

# Debug info
print("Super price: " + str(price_super))
print("Super percentile: " + str(p_super))
print("----------------------------")
print("Diesel price: " + str(price_diesel))
print("Diesel percentile: " + str(p_diesel))
print("----------------------------")

# Compare the super and diesel with the percentiles and sent an email if needed
if price_super < p_super:
    msg = "Super ist mit " + str(price_super) + "cent recht guenstig"
    send_mail(email_receiver_super, msg)
    print("Super notification sent")
if price_diesel < p_diesel:
    msg = "Diesel ist mit " + str(price_diesel) + "cent recht guenstig"
    send_mail(email_receiver_diesel, msg)
    print("Diesel notification sent")
