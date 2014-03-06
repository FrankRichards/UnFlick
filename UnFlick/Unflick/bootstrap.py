import hashlib
import mimetypes
import os
import shelve
import string
import sys
import time
import urllib.request, urllib.error, urllib.parse
import email.generator
import webbrowser
import xml.etree.ElementTree as etree
import sqlite3


#   Flickr settings
#
FLICKR = {
        "api_key" : "0599678bc8fbb043cf90eec10f00b86f",
        "secret" : "ba919e10fe2e011d"
    }

class APIConstants:
    """ APIConstants class 
    """

    base = "http://flickr.com/services/"
    rest   = base + "rest/"
    auth   = base + "auth/"
    photos = base + "photos/"
    
    token = "auth_token"
    secret = "secret"
    key = "api_key"
    sig = "api_sig"
    frob = "frob"
    perms = "perms"
    method = "method"
    
    def __init__( self ):
        """ Constructor
       """
        pass
       
api = APIConstants()

class Downloadr:
    """ Downloadr class 
    """
    
    token = None
    perms = ""
    TOKEN_FILE = ".flickrToken"
    numpages = 0
    
    def __init__( self ):
        """ Constructor
        """
        self.token = self.getCachedToken()



    def signCall( self, data):
        """
        Signs args via md5 per http://www.flickr.com/services/api/auth.spec.html (Section 8)
        """
        keys = list(data.keys())
        keys.sort()
        foo = ""
        for a in keys:
            foo += (a + data[a])
        
        f = FLICKR[ api.secret ] + api.key + FLICKR[ api.key ] + foo
        #f = api.key + FLICKR[ api.key ] + foo
        return hashlib.md5( f.encode('utf-8') ).hexdigest()
   
    def urlGen( self , base,data, sig ):
        """ urlGen
        """
        foo = base + "?"
        for d in data: 
            foo += d + "=" + data[d] + "&"
        return foo + api.key + "=" + FLICKR[ api.key ] + "&" + api.sig + "=" + sig
        
 
    def authenticate( self ):
        """ Authenticate user so we can upload images
        """

        print("Getting new Token")
        self.getFrob()
        self.getAuthKey()
        self.getToken()   
        self.cacheToken()

    def getFrob( self ):
        """
        flickr.auth.getFrob
    
        Returns a frob to be used during authentication. This method call must be 
        signed.
    
        This method does not require authentication.
        Arguments
    
        api.key (Required)
        Your API application key. See here for more details.     
        """
    

        d = { 
            api.method  : "flickr.auth.getFrob"
            }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            response = self.getResponse( url )
            if ( self.isGood( response ) ):
                FLICKR[ api.frob ] = response.find('frob').text
            else:
                self.reportError( response )
        except:
            print (("Error getting frob:" , str( sys.exc_info() )))

    def getAuthKey( self ): 
        """
        Checks to see if the user has authenticated this application
        """
        d =  {
            #api.frob : FLICKR[ api.frob ], 
            api.frob : str(FLICKR[ api.frob ]), 
            api.perms : "read"  
            }
        sig = self.signCall( d )
        url = self.urlGen( api.auth, d, sig )
        ans = ""
        try:
            webbrowser.open( url )
            print(url)
            ans = input("Have you authenticated this application? (Y/N): ")
        except:
            print((str(sys.exc_info())))
        if ( ans.lower() == "n" ):
            print("You need to allow this program to access your Flickr site.")
            print("A web browser should pop open with instructions.")
            print("After you have allowed access restart uploadr.py")
            sys.exit()    

    def getToken( self ):
        """
        http://www.flickr.com/services/api/flickr.auth.getToken.html
        
        flickr.auth.getToken
    
        Returns the auth token for the given frob, if one has been attached. This method call must be signed.
        Authentication
    
        This method does not require authentication.
        Arguments
    
        NTC: We need to store the token in a file so we can get it and then check it instead of
        getting a new on all the time.
        
        api.key (Required)
           Your API application key. See here for more details.
        frob (Required)
           The frob to check.         
        """   

        d = {
            api.method : "flickr.auth.getToken",
            api.frob : str(FLICKR[ api.frob ])
        }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            res = self.getResponse( url )
            if ( self.isGood( res ) ):
                self.token = str(res.find('auth').find('token').text)
                self.perms = str(res.find('auth').find('perms').text)
                self.cacheToken()
            else :
                self.reportError( res )
        except:
            print((str(sys.exc_info())))

    def getCachedToken( self ): 
        """
        Attempts to get the flickr token from disk.
       """
        if ( os.path.exists( self.TOKEN_FILE )):
            return open( self.TOKEN_FILE ).read()
        else :
            return None
        


    def cacheToken( self ):
        """ cacheToken
        """

        try:
            open( self.TOKEN_FILE , "w").write( str(self.token) )
        except:
            print(("Issue writing token to local cache " , str(sys.exc_info())))

    def checkToken( self ):    
        """
        flickr.auth.checkToken

        Returns the credentials attached to an authentication token.
        Authentication
    
        This method does not require authentication.
        Arguments
    
        api.key (Required)
            Your API application key. See here for more details.
        auth_token (Required)
            The authentication token to check. 
        """

        if ( self.token == None ):
            return False
        else :
            d = {
                api.token  :  str(self.token) ,
                api.method :  "flickr.auth.checkToken"
            }
            sig = self.signCall( d )
            url = self.urlGen( api.rest, d, sig )     
            try:
                res = self.getResponse( url ) 
                if ( self.isGood( res ) ):
                    self.token = str(res.find('auth').find('token').text)
                    self.perms = str(res.find('auth').find('perms').text)
                    self.nsid = str(res.find('auth').find('user').attrib['nsid'])
                    return True
                else :
                    self.reportError( res )
            except:
                print((str(sys.exc_info())))
            return False
        
    def getfirst(self):
        #Get the first page of images. The important thing
        #is the number of pages, to set up the for loop.
        d = { 
            api.method  : "flickr.photos.search",
            "user_id" : self.nsid,
            "per_page" : "25",
            "extras" : "url_o",
            "auth_token" : self.token
            }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        print(url)
        res = self.getResponse(url)
        self.numpages = int(res.find("photos").attrib['pages'])
        
    def getimg(self, url):
        #fetch the image whose url is url.
        res = self.getResponse(url)
        print(res)
        
        
     
             
    def download( self ):
        """
        This is a full download of your Flickr account:
        Images, sets and groups. Note, images are not duplicated, just the references
        """
        self.getfirst()
        #SQLite version clears table.
        cursor.execute('delete from image')
        cnx.commit()
        d = { 
            api.method  : "flickr.photos.search",
            "user_id" : self.nsid,
            "per_page" : "25",
            "extras" : "url_o,date_taken,date_upload,description",
            "auth_token" : self.token,
            "page" : "1"
            }
        #numpages was read in getFirst().
        #interate over pages.
        for i in range( self.numpages):
            d["page"] = str(i+1)
            sig = self.signCall( d )
            url = self.urlGen( api.rest, d, sig )
            print(url)
            res = self.getResponse(url)
            piclist = res.iter("photo")
            #iterate over images on the page
            for thispic in piclist:
                
                picurl = thispic.attrib["url_o"]
                print( picurl)
                img = urllib.request.urlopen( picurl ).read()

                #note, you ask for date_taken and get back datetaken 
                
                insertSQL = """INSERT INTO image( id , owner ,
                secret ,server , farm , title ,
                url_o , height_o ,width_o ,
                date , image ) VALUES ( + 'thispic.attrib["id"]' + ,
                'thispic.attrib["owner"]' + , + 'thispic.attrib["secret"]' + ","
                thispic.attrib["server"] + , + thispic.attrib["farm"] + ","
                thispic.attrib["title"] + ,
                thispic.attrib["url_o"] + ,
                thispic.attrib["height_o"] + ,
                thispic.attrib["width_o"] + ,
                thispic.attrib["datetaken"] + ,'%s')"""
    
                cursor.execute("""INSERT INTO image( id , owner ,
                secret ,server , farm , title ,
                url_o , height_o ,width_o ,
                date , upload, description, image ) VALUES ( ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?)""", ( int(thispic.attrib["id"]), thispic.attrib["owner"],
                                      thispic.attrib["secret"], thispic.attrib["server"],
                                      thispic.attrib["farm"], 
                                      thispic.attrib["title"],
                                      thispic.attrib["url_o"],
                                      thispic.attrib["height_o"],
                                      thispic.attrib["width_o"],
                                      thispic.attrib["datetaken"],
                                      int(thispic.attrib["dateupload"]),
                                      thispic.find("description").text,
                                      img ))
                print(thispic.attrib["id"])
                cnx.commit()

    def isGood( self, res ):
        """ isGood
        """

        if ( res.attrib['stat'] == "ok" ):
            return True
        else :
            return False
            
            
    def reportError( self, res ):
        """ reportError
        """

        try:
            print(("Error:", str( res.find('err').attrib['code'] + " " + res.find('err').attrib['msg'] )))
        except:
            print(("Error: " + str( res )))

    def getResponse( self, url ):
        """
        Send the url and get a response.  Let errors float up
        """

        xml = urllib.request.urlopen( url ).read()
        print(xml)
        root = etree.fromstring( xml )
        return root
            
     
if __name__ == "__main__":
    print('howdy')
    flick = Downloadr()
    if ( not flick.checkToken() ):
            flick.authenticate()
            
      
    cnx = sqlite3.connect("/home/frank/flickrback")
    cursor = cnx.cursor()
    flick.download()
    print("all done")
