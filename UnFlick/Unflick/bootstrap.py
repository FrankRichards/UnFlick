import hashlib
import os
import sys
import urllib.request, urllib.error
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
        """ Authenticate user so we can download images
        """
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
            #print(url)
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
        
    def getFirst(self):
        #Get the first page of images. The important thing
        #is the number of pages, to set up the for loop.
        d = { 
            api.method  : "flickr.photos.search",
            "user_id" : self.nsid,
            "per_page" : "100",
            "extras" : "url_o",
            "auth_token" : self.token
            }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        res = self.getResponse(url)
        self.numpages = int(res.find("photos").attrib['pages'])
        
    def getimg(self, url):
        #fetch the image whose url is url.
        res = self.getResponse(url)
        
        
     
             
    def download( self ):
        """
        This is a full download of your Flickr account:
        Images, sets and groups. Note, images are not duplicated, just the references
        """
        self.getFirst()
        #SQLite version clears table.
        self.reInitDB()
        d = { 
            api.method  : "flickr.photos.search",
            "user_id" : self.nsid,
            "per_page" : "100",
            "extras" : "url_o,date_taken,date_upload,description,views",
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
                while True:
                    try:
                        img = urllib.request.urlopen( picurl ).read()
                    except urllib.error.HTTPError:
                        continue
                    break  #kludge. must be a better way

                #note, you ask for date_taken and get back datetaken 
                
                cursor.execute("""INSERT INTO image( id , owner ,
                secret ,server , farm , title ,
                url_o , height_o ,width_o ,
                date , upload, views, description, image ) VALUES ( ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?)""", ( int(thispic.attrib["id"]), thispic.attrib["owner"],
                                      thispic.attrib["secret"], thispic.attrib["server"],
                                      thispic.attrib["farm"], 
                                      thispic.attrib["title"],
                                      thispic.attrib["url_o"],
                                      thispic.attrib["height_o"],
                                      thispic.attrib["width_o"],
                                      thispic.attrib["datetaken"],
                                      int(thispic.attrib["dateupload"]),
                                      int(thispic.attrib["views"]),
                                      thispic.find("description").text,
                                      img ))
                print(thispic.attrib["id"])
                cnx.commit()
                self.getPicComments(thispic.attrib["id"])
        self.getSets()
        
    def getPicComments(self, picID):
        """ Grab the comments on the set
        """
        d = { 
             api.method  : "flickr.photos.comments.getList",
             "user_id" : self.nsid,
             "auth_token" : self.token,
             "photo_id" : picID,
             } 
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        res = self.getResponse(url)
        commentList = res.iter("comment")
        for thisComment in commentList:
            cursor.execute("""INSERT INTO comments(
                id, author_id, author_name,date_create, permalink, text)
                values ( ?, ?, ?, ?, ?, ?)""",
                (thisComment.attrib["id"],
                 thisComment.attrib["author"],
                 thisComment.attrib["authorname"],
                 thisComment.attrib["datecreate"],
                 thisComment.attrib["permalink"],
                 thisComment.text))
            cnx.commit()
            cursor.execute("""INSERT INTO piccomments (
                pic_id, comment_id) values (?, ?)""",
                (picID, thisComment.attrib["id"]))
            cnx.commit()

                
    def getSets(self):
        """ Download the list of sets
        """
        d = { 
            api.method  : "flickr.photosets.getlist",
            "user_id" : self.nsid,
            "auth_token" : self.token,
            } 
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        res = self.getResponse(url)       
        setlist = res.iter("photoset")
        for thisset in setlist:
            cursor.execute("""INSERT INTO sets(id, primary_pic, secret,
                server, farm, photos, videos, views, comments, date_created, date_updated,
                title, description)
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(thisset.attrib["id"]), int(thisset.attrib["primary"]), thisset.attrib["secret"],
                int(thisset.attrib["server"]), int(thisset.attrib["farm"]),
                int(thisset.attrib["photos"]), int(thisset.attrib["videos"]),
                int(thisset.attrib["count_views"]), int(thisset.attrib["count_comments"]),
                int(thisset.attrib["date_create"]), int(thisset.attrib["date_update"]),
                thisset.find("title").text, thisset.find("description").text))
            cnx.commit()
            self.getSetPics(thisset.attrib["id"])
            
    def getSetPics(self, setID):
        d = { 
            api.method  : "flickr.photosets.getPhotos",
            "user_id" : self.nsid,
            "auth_token" : self.token,
            "photoset_id" : setID,
            "per_page" : "25"
        } 
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        res = self.getResponse(url)
        setPages = int(res.find("photoset").attrib["pages"])
        for i in range( setPages):
            d["page"] = str(i + 1)
            sig = self.signCall( d )
            url = self.urlGen( api.rest, d, sig )
            print(url)
            res = self.getResponse(url)
            piclist = res.iter("photo")
            for thisPic in piclist:
                cursor.execute("""INSERT INTO setpics(pic_id, set_id)
                    values(?, ?)""", (int(thisPic.attrib["id"]), int(setID)))
                cnx.commit()
                
    def getSetComments(self, setID):
        """ Grab the comments on the set
        """
        d = { 
            api.method  : "flickr.photosets.comments.getList",
            "user_id" : self.nsid,
            "auth_token" : self.token,
            "photoset_id" : setID,
        } 
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        print(url)
        res = self.getResponse(url)
        commentList = res.iter("comment")
        for thisComment in commentList:
            cursor.execute("""INSERT INTO comments(
                id, author_id, author_name,date_create, permalink, text)
                values ( ?, ?, ?, ?, ?, ?)""",
                (thisComment.attrib["id"],
                thisComment.attrib["author"],
                thisComment.attrib["authorname"],
                thisComment.attrib["date_create"],
                thisComment.attrib["permalink"],
                thisComment.text))
            cnx.commit()
            cursor.execute("""INSERT INTO setcomments (
                set_id, comment_id) values (?, ?)""",
                (setID, thisComment.attrib["id"]))
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
    
    def reInitDB(self):
        """
        Drop and recreate all the tables.
        Don't bother vacuuming (truncating).
        This is prelude to a full backup.
        """
        cursor.execute("DROP TABLE IF EXISTS setpics")
        cursor.execute("DROP TABLE IF EXISTS setcomments")
        cursor.execute("DROP TABLE IF EXISTS piccomments")
        cursor.execute("DROP TABLE IF EXISTS comments")
        cursor.execute("DROP TABLE IF EXISTS sets")
        cursor.execute("DROP TABLE IF EXISTS image")
        cnx.commit()
        
        cursor.execute("""CREATE TABLE image (    
            id int primary key,
            owner char(12),
            secret char(10),
            server int,
            farm int,
            title varchar(120),
            url_o varchar(120),
            height_o int,
            width_o int,
            date datetime,
            upload int,
            views int,
            description clob,
            image blob
            );""")
        cnx.commit()
        cursor.execute("""CREATE TABLE sets (
            id int primary key,
            primary_pic int,
            secret char(12),
            server int,
            farm int,
            photos int,
            videos int,
            views int,
            comments int,
            date_created int,
            date_updated int,
            title varchar(120),
            description clob
        );""")
        cnx.commit()
        cursor.execute("""CREATE TABLE comments (
            id varchar(40) primary key,
            author_id varchar(20),
            author_name varchar(72),
            date_create int,
            permalink varchar(100),
            text clob
        );""")
        cnx.commit()
        cursor.execute("""CREATE TABLE setcomments (
            set_id integer references sets(id),
            comment_id varchar(40) references comments(id)
        );""")
        cnx.commit()
        cursor.execute("""CREATE TABLE piccomments (
            pic_id int references image(id),
            comment_id varchar(40) references comments(id)
        );""")
        cursor.execute("""CREATE TABLE setpics (
            pic_id integer references image(id),
            set_id integer references sets(id)
        );""")
        
            
     
if __name__ == "__main__":
    flick = Downloadr()
    if ( not flick.checkToken() ):
            flick.authenticate()
            
      
    cnx = sqlite3.connect('/home/frank/flickrback')
    cursor = cnx.cursor()
    cursor.execute("pragma foreign_keys=TRUE")
    cnx.commit()
    flick.download()
    #flick.reInitDB()
    #flick.getSets()
    print("all done")
