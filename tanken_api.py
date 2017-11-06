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
sqlite3.register_adapter(bool, int)
sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))


class Price(object):
    def __init__(self, super_price, diesel_price, super_sent=False, diesel_sent=False):
        self.super_price = super_price
        self.diesel_price = diesel_price
        self.super_sent = super_sent
        self.diesel_sent = diesel_sent


def create_table():
    try:
        sql_command = """
        CREATE TABLE 'preis' ( 
        time INTEGER PRIMARY KEY, 
        price_super INTEGER, 
        price_diesel INTEGER,
        super_sent INTEGER DEFAULT 0,
        diesel_sent INTEGER DEFAULT 0
        );"""
        cursor.execute(sql_command)
    except sqlite3.OperationalError:
        pass


def insert_into_db(price):
    millis = int(round(time.time() * 1000))
    format_str = """INSERT INTO 'preis' (time, price_super, price_diesel, super_sent, diesel_sent)
    VALUES ("{time}", "{price_super}", "{price_diesel}", "{super_sent}", "{diesel_sent}");"""
    sql_command = format_str.format(time=millis, price_super=price.super_price, price_diesel=price.diesel_price,
                                    super_sent=(1 if price.super_sent else 0),
                                    diesel_sent=(1 if price.diesel_sent else 0))
    cursor.execute(sql_command)
    connection.commit()


def get_percentiles():
    millis = int(round(time.time() * 1000))
    # Nur die letzten 5 Tage berücksichtigen
    millis_days_ago = str(millis - (days_for_percentile * 24 * 60 * 60 * 1000))
    cursor.execute(
        "SELECT price_super, price_diesel, super_sent, diesel_sent FROM preis WHERE time > " + millis_days_ago +
        " ORDER BY time DESC")

    super_prices = []
    diesel_prices = []
    results_db = cursor.fetchall()
    if len(results_db) == 0:
        return None
    for line in results_db:
        super_prices.append(int(line[0]))
        diesel_prices.append(int(line[1]))
    last = results_db[0]
    last_prices_db = Price(super_price=last[0], diesel_price=last[1], super_sent=bool(last[2]),
                           diesel_sent=bool(last[3]))
    # use numpy to generate a percentile
    super_percentile_value = np.percentile(np.array(super_prices), alert_percentile)
    diesel_percentile_value = np.percentile(np.array(diesel_prices), alert_percentile)
    return [[super_percentile_value, diesel_percentile_value], last_prices_db]


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

    return Price(current_price_super, current_price_diesel)


# Just try to create the table each time in case it does not exist.
create_table()

# Load current prices and store them into vars
price = load_current_prices()

# Load the percentiles by fetching values from db
percentile_array = get_percentiles()
if percentile_array is None:
    print("Using defaults as this is the first run. If not your database might be corrupt")
    # reset to defaults as this is the first run
    p_super = 1000
    p_diesel = 1000
    last_prices = Price(1000, 1000, False, False)
else:
    p_super = percentile_array[0][0]
    p_diesel = percentile_array[0][1]
    last_prices = percentile_array[1]

# Debug info
print("Super price: " + str(price.super_price))
print("Super percentile: " + str(p_super))
print("----------------------------")
print("Diesel price: " + str(price.diesel_price))
print("Diesel percentile: " + str(p_diesel))
print("----------------------------")

# Compare the super and diesel with the percentiles and sent an email if needed
if price.super_price <= p_super:
    price.super_sent = True
    if not last_prices.super_sent:
        msg = "Super ist mit " + str(price.super_price) + "cent recht guenstig"
        send_mail(email_receiver_super, msg)
        print("Super notification sent")
if price.diesel_price <= p_diesel:
    price.diesel_sent = True
    if not last_prices.diesel_sent:
        msg = "Diesel ist mit " + str(price.diesel_price) + "cent recht guenstig"
        send_mail(email_receiver_diesel, msg)
        print("Diesel notification sent")

# Insert the prices into the db
insert_into_db(price)
