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
        print('h1')
        """ download
        """
        self.getfirst()
                d = { 
            api.method  : "flickr.photos.search",
            "user_id" : self.nsid,
            "per_page" : "25",
            "extras" : "url_o",
            "auth_token" : self.token
            }
        i = 1
        while i <= self.numpages:
            d
            page = getresponse()
 
        #self.uploaded = shelve.open( HISTORY_FILE )
        #for image in newImages:
        #    self.uploadImage( image )
        #self.uploaded.close()
                   
    
    def uploadImage( self, image ):
        """ uploadImage
        """

        if ( image not in self.uploaded ):
            print(("Uploading ", image , "...",))
            try:
                photo = ('photo', image, open(image,'rb').read())
                d = {
                    api.token   : self.token,
                    #api.perms   : self.perms,
                    "title"     : FLICKR["title"],
                    "description":FLICKR["description"],
                    "tags"      : FLICKR["tags"],
                    "is_public" : FLICKR["is_public"],
                    "is_friend" : FLICKR["is_friend"],
                    "is_family" : FLICKR["is_family"]
                }
                sig = self.signCall( d )
                d[ api.sig ] = sig
                d[ api.key ] = FLICKR[ api.key ]        
                url = self.build_request(api.upload, d, (photo,))    
                xml = urllib.request.urlopen( url ).read()
                res = etree.fromstring(xml)
                if ( self.isGood( res ) ):
                    print("successful.")
                    self.logUpload( res.find('photoid').text, image )
                else :
                    print("problem..")
                    self.reportError( res )
            except:
                print((str(sys.exc_info())))


    def logUpload( self, photoID, imageName ):
        """ logUpload
        """

        photoID = str( photoID )
        imageName = str( imageName )
        self.uploaded[ imageName ] = photoID
        self.uploaded[ photoID ] = imageName
            
    def build_request(self, theurl, fields, files, txheaders=None):
        """
        build_request/encode_multipart_formdata code is from www.voidspace.org.uk/atlantibots/pythonutils.html

        Given the fields to set and the files to encode it returns a fully formed urllib2.Request object.
        You can optionally pass in additional headers to encode into the object. (Content-type and Content-length will be overridden if they are set).
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.    
        """

        content_type, body = self.encode_multipart_formdata(fields, files)
        if not txheaders: txheaders = {}
        txheaders['Content-type'] = content_type
        txheaders['Content-length'] = str(len(body))
        return urllib.request.Request(theurl, body, txheaders)     

    def encode_multipart_formdata(self,fields, files, BOUNDARY = '-----'+email.generator._make_boundary()+'-----'):
        """ Encodes fields and files for uploading.
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.
        Return (content_type, body) ready for urllib2.Request instance
        You can optionally pass in a boundary string to use or we'll let mimetools provide one.
        """    

        CRLF = '\r\n'
        L = []
        if isinstance(fields, dict):
            fields = list(fields.items())
        for (key, value) in fields:   
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        body = CRLF.join(L).encode('utf-8')
        for (key, filename, value) in files:
            L = []
            filetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            L.append('')
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % filetype)
            L.append('')
            L.append('')
            body += CRLF.join(L).encode('utf-8') + value
        end = []
        end.append('')
        end.append('--' + BOUNDARY + '--')
        end.append('')
        body += CRLF.join(end).encode('utf-8')
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY        # XXX what if no files are encoded
        return content_type, body
    
    
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
            

    def run( self ):
        """ run
        """

      
if __name__ == "__main__":
    print('howdy')
    flick = Downloadr()
    if ( not flick.checkToken() ):
            flick.authenticate()
    
    if ( len(sys.argv) >= 2  and sys.argv[1] == "-d"):
        flick.run()
    else:
        flick.download()
