
import mysql.connector
import urllib
import os

cnx = mysql.connector.connect(user='frank', database='flickrback', p='wench99whip')
cursor = cnx.cursor()

