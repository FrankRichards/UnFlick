
import mysql.connector
import urllib
import os

cnx = mysql.connector.connect(user='frank', database='flickrback', password='wench99whip')
cursor = cnx.cursor()

