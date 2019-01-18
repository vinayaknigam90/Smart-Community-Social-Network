# from __future__ import print_function
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

cursor.execute("DROP TABLE IF EXISTS users CASCADE")
# cursor.execute("DROP TABLE IF EXISTS Users CASCADE")
# cursor.execute("DROP TABLE IF EXISTS community1 CASCADE")
#Community Query
# cursor.execute("INSERT INTO Community (name, address, city, zip_code, creation_date)VALUES('Community1', 'avalon', 'San Jose', 95112, current_timestamp)")
#
# # Users query
#
# cursor.execute("INSERT INTO Users VALUES('rahil15', 1, 'rahil', 'modi', 'rahil@gmail.com', 'rahil', '1111111111')")

# cursor.execute("INSERT INTO Users VALUES('rahil15', 1, 'rm@gmail.com','rahil', '1111111111')")
# cursor.execute("DROP TABLE IF EXISTS Users CASCADE")
# cursor.execute("DROP TABLE IF EXISTS Apartments CASCADE")
# cursor.execute("DROP TABLE IF EXISTS ApartmentTypes CASCADE")





#Apartments Table
# cursor.execute("CREATE TABLE Apartments(apartmentId INT PRIMARY KEY , typeId INT references ApartmentTypes(Id), lease_start DATE, lease_end DATE)")
# cursor.execute("INSERT INTO Apartments VALUES(1,1, '10/10/2017', '10/09/2018')")
# cursor.execute("INSERT INTO Apartments VALUES(2,2, '10/10/2017', '10/09/2018')")

# User and Apartments Table
# cursor.execute("CREATE TABLE UserApartment(apartmentID INT references Apartments(apartmentId), userID VARCHAR references Users(username))")
# cursor.execute("INSERT INTO UserApartment VALUES(1, 'rahil15')")

conn.commit()

# cursor.execute("""SELECT * from community""")
# rows = cursor.fetchall()
#
# print "\nShow me the databases:\n"
# pprint.pprint(rows)

# cursor.execute("""SELECT * from Users""")
# rows = cursor.fetchall()
#
# print "\nShow me the databases:\n"
# pprint.pprint(rows)
