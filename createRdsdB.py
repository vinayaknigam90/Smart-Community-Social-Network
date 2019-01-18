import psycopg2
import sys
import pprint
import datetime

#Enter the values for you database connection
dsn_database = "socialCommunity"            # e.g. "compose"
dsn_hostname =  "social-community.cznwlohjgx0g.us-west-2.rds.amazonaws.com" # e.g.: "aws-us-east-1-portal.4.dblayer.com"
dsn_port = "5432"                 # e.g. 11101
dsn_uid = "myawsuser"        # e.g. "admin"
dsn_pwd = "myawsuser"      # e.g. "xxx"

try:
    conn_string = "host="+dsn_hostname+" port="+dsn_port+" dbname="+dsn_database+" user="+dsn_uid+" password="+dsn_pwd
    print ("Connecting to database \n")
    conn=psycopg2.connect(conn_string)
    print ("Connected!\n")
except:
    print ("Unable to connect to the database.")

cursor = conn.cursor()

#Community Table
cursor.execute("DROP TABLE IF EXISTS Community CASCADE")
cursor.execute("CREATE TABLE Community(ID SERIAL PRIMARY KEY, name VARCHAR(26), address VARCHAR(26), \
city VARCHAR(40), zip_code INT, creation_date DATE)")

# Users Table
cursor.execute("DROP TABLE IF EXISTS Users CASCADE")
cursor.execute("CREATE TABLE Users(username VARCHAR(25) UNIQUE, communityID INT references Community(ID), \
firstName VARCHAR(40), lastName VARCHAR(40), email VARCHAR(40) PRIMARY KEY, password VARCHAR(40), \
contact_number VARCHAR(30))")

conn.commit()
