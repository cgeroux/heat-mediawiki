#!/usr/bin/python3
import optparse as op
import os
import shutil
import subprocess
import glob
import string
import random
import stat
import re

def parseOptions():
  """Parses command line options
  """
  
  parser=op.OptionParser(usage="Usage %prog"
    ,version="%prog 1.0",description="Sets up mediawiki")
  
  #parse command line options
  return parser.parse_args()
def replaceStrInFile(strMatch,strReplace,fileName,maxOccurs=None):
  """Replace all occurrences of strMatch with strReplace in file fileName
  up to maxOccurs if specified.
  """
  
  file=open(fileName,mode='r')
  fileText=file.read()
  file.close()
  
  #how many occurrences are there
  numMatches=fileText.count(strMatch)
  
  if maxOccurs!=None:
    fileText=fileText.replace(strMatch,strReplace,max=maxOccurs)
    if numMatches>maxOccurs:
      numMatches=maxOccurs
  else:
    fileText=fileText.replace(strMatch,strReplace)
  file=open(fileName,mode='w')
  file.write(fileText)
  file.close()
  return numMatches
def replaceStrInFileRe(pattern,replacement,fileName,maxOccurs=None):
  """Replace all occurrences of pattern with strReplace in file fileName
  up to maxOccurs if specified. This version uses regular expression matching 
  also
  """
  
  file=open(fileName,mode='r')
  fileText=file.read()
  file.close()
  
  #how many occurrences are there
  numMatches=len(re.findall(pattern,fileText))
  
  if maxOccurs!=None:
    fileText=re.sub(pattern,replacement,fileText,count=maxOccurs)
    if numMatches>maxOccurs:
      numMatches=maxOccurs
  else:
    fileText=re.sub(pattern,replacement,fileText)
  file=open(fileName,mode='w')
  file.write(fileText)
  file.close()
  return numMatches
def appendToFile(strsToAppend,fileName):
  """Append multiple string to the end of a file
  """
  
  file=open(fileName,mode='r')
  fileText=file.read()
  file.close()
  for strToAppend in strsToAppend:
    fileText+=strToAppend
  file=open(fileName,mode='w')
  file.write(fileText)
  file.close()
def genNameAndPass(length=16
  ,chars=string.ascii_uppercase+string.ascii_lowercase+string.digits):
  
  name=''
  for i in range(length):
    name+=random.SystemRandom().choice(chars)
    
  passwd=''
  for i in range(length):
    passwd+=random.SystemRandom().choice(chars)
  
  return (name,passwd)
def setupMediaWiki(settings={}):
  """Downloads media wiki and puts it into document root
  """
  
  (adminName,adminPassWd)=genNameAndPass()
  (dummy,dbPassWd)=genNameAndPass()
  
  defaultSettings={
    "version":"1.27"
    ,"patch":"0"
    ,"wikiName":"Test Wiki"
    ,"wikiReadPerm":"user"          #public, user, sysop
    ,"wikiEditPerm":"user"          #public, user, sysop
    ,"wikiAccCreatePerm":"sysop"    #public, user, sysop
    ,"wikiAdminName":adminName
    ,"wikiAdminPass":adminPassWd
    ,"server":"http://206.167.181.71"
    ,"dbserver":"localhost"
    ,"dbuser":"root"
    ,"dbpass":dbPassWd
    ,"documentRoot":"/var/www/html"
    ,"tmpDir":"/tmp"
    ,"owner":"www-data"
    ,"group":"www-data"
    ,"cleanUp":True
    ,"purgeDocRoot":True
    ,"enableUploads":False
    ,"logoURL":"$wgResourceBasePath/resources/assets/cc-cloud-wiki-logo.png"
    ,"extraConfigLines":[]
    }
  
  #set settings to default if no settings given or if setting is None
  for key in defaultSettings.keys():
    
    if key not in settings.keys():
      settings[key]=defaultSettings[key]
    else:
      if settings[key]==None:
        settings[key]=defaultSettings[key]
  
  tmpMediaWikiDir=os.path.join(settings["tmpDir"],"mediawiki-"
    +settings["version"]+"."+settings["patch"])
  url="https://releases.wikimedia.org/mediawiki/"+settings["version"] \
    +"/mediawiki-"+settings["version"]+"."+settings["patch"]+".tar.gz"
  
  #download and untar mediawiki
  subprocess.call(["wget",url,"--directory-prefix="+settings["tmpDir"]])
  subprocess.call(["tar","-xzf",tmpMediaWikiDir+".tar.gz","-C"
    ,settings["tmpDir"]])
  
  #remove existing files in document root
  if settings["purgeDocRoot"]:
    paths=glob.glob(settings["documentRoot"]+"/*")
    for path in paths:
      try:
        os.remove(path)
      except IsADirectoryError:
        shutil.rmtree(path)
  
  #move files to document root
  paths=glob.glob(tmpMediaWikiDir+"/*")
  for path in paths:
    pathBaseName=os.path.basename(path)
    shutil.move(path,os.path.join(settings["documentRoot"],pathBaseName))
  
  #change owner and group
  for path in paths:
    pathBaseName=os.path.basename(path)
    shutil.chown(os.path.join(settings["documentRoot"],pathBaseName)
      ,user=settings["owner"]
      ,group=settings["group"])
  
  #clean up temporary files
  if settings["cleanUp"]:
    os.removedirs(tmpMediaWikiDir)
    os.remove(tmpMediaWikiDir+".tar.gz")
  
  #set mysql root password (initial install has no root password)
  subprocess.call(["mysqladmin","-u","root","password",settings["dbpass"]])
  
  #do basic configure of the wiki
  subprocess.call(["php"
    ,os.path.join(settings["documentRoot"],"maintenance/install.php")
    ,"--scriptpath", ""
    ,"--pass",settings["wikiAdminPass"]
    ,"--server",settings["server"]
    ,"--dbuser",settings["dbuser"]
    ,"--dbpass",settings["dbpass"]
    ,"--dbserver",settings["dbserver"]
    ,settings["wikiName"]
    ,settings["wikiAdminName"]])
  
  localSettingsFile=os.path.join(settings["documentRoot"],"LocalSettings.php")
  
  #enable file uploads
  if settings["enableUploads"]:
    replaceStrInFile("$wgEnableUploads = false;","$wgEnableUploads = true;"
      ,localSettingsFile)
  
  #copy default cc-wiki-logo
  src=os.path.join(settings["tmpDir"]
    ,"cloud-init-mediawiki/cc-cloud-wiki-logo.png")
  dest=os.path.join(settings["documentRoot"]
    ,"resources/assets/cc-cloud-wiki-logo.png")
  shutil.copy(src,dest)
  
  #set logo
  replaceStrInFile(
    "$wgLogo = \"$wgResourceBasePath/resources/assets/wiki.png\";"
    ,"$wgLogo = \""+settings["logoURL"]+"\";"
    ,localSettingsFile)
    
  #disable emails as no email client is configured
  replaceStrInFile("$wgEnableEmail = true;","$wgEnableEmail = false;"
    ,localSettingsFile)
  replaceStrInFile("$wgEnableUserEmail = true;","$wgEnableUserEmail = false;"
    ,localSettingsFile)
  
  
  #secure LocalSettings.php, only owner needs read access
  shutil.chown(localSettingsFile,user=settings["owner"]
    ,group=settings["group"])
  os.chmod(localSettingsFile,0o400)
  
  #Set read permissions
  if settings["wikiReadPerm"]=="user" or settings["wikiReadPerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['*']['read'] = false;\n"]
      ,localSettingsFile)
    if settings["enableUploads"]:
      print("WARNING: read permission not public but uploads are enabled."
        +" The public will still be able to see uploads if they know the "
        +"correct url to go directly to the file.")
  if settings["wikiReadPerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['user']['read'] = false;\n"]
      ,localSettingsFile)
    
  #ensure the login page is always readable
  appendToFile(["$wgWhitelistRead = array (\"Special:Userlogin\");\n"]
    ,localSettingsFile)
  
  #Set edit permissions
  if settings["wikiEditPerm"]=="user" or settings["wikiEditPerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['*']['edit'] = false;\n"]
      ,localSettingsFile)
  if settings["wikiEditPerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['user']['edit'] = false;\n"]
      ,localSettingsFile)
  
  #Set account creation permissions
  if settings["wikiAccCreatePerm"]=="user" \
    or settings["wikiAccCreatePerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['*']['createaccount'] = false;\n"]
      ,localSettingsFile)
  if settings["wikiAccCreatePerm"]=="sysop":
    appendToFile(["$wgGroupPermissions['user']['createaccount'] = false;\n"]
      ,localSettingsFile)
  
  #add any extra configuration options explicitly set
  appendToFile(settings["extraConfigLines"],localSettingsFile)
  
  return (settings["wikiAdminName"],settings["wikiAdminPass"])
def securePHP():
  """Ensures some basic php security settings are set
  """
  
  #ensure register_globals is disabled
  numReplaces=replaceStrInFileRe(
    "(?<!([^\s]))register_globals[\s]*=[\s]*((O|o)n|(O|o)ff)"
    ,"register_globals = Off","/etc/php5/apache2/php.ini")
  if numReplaces==0:#if no strings replaced add it
    appendToFile("register_globals = Off\n","/etc/php5/apache2/php.ini")
  
  #disable allow_url_fopen
  numReplaces=replaceStrInFileRe(
    "(?<!([^\s]))allow_url_fopen[\s]*=[\s]*((O|o)n|(O|o)ff)"
    ,"allow_url_fopen = Off","/etc/php5/apache2/php.ini")
  if numReplaces==0:#if no strings replaced add it
    appendToFile("allow_url_fopen = Off\n","/etc/php5/apache2/php.ini")
  
  #ensure session.use_trans_sid is off
  numReplaces=replaceStrInFileRe(
    "(?<!([^\s]))session.use_trans_sid[\s]*=[\s]*[0-1]"
    ,"session.use_trans_sid = 0","/etc/php5/apache2/php.ini")
  if numReplaces==0:#if no strings replaced add it
    appendToFile("session.use_trans_sid = 0\n","/etc/php5/apache2/php.ini")
  
  #restart apache for settings to take effect
  restartApache()
def secureMySQL():
  """Ensures some basic MySQL security settings are set
  """
  #TODO: implement
  pass
def secureApache():
  """
  """
  #TODO: implement
  pass
def restartApache():
  """Restarts apache2
  """
  
  subprocess.call(["service","apache2","restart"])
def main():
  
  #parse command line options
  (options,args)=parseOptions()
  
  #adjust some php settings to improve security
  securePHP()
  
  #adjust some mysql settings to improve security
  secureMySQL()
  
  #adjust some apache settings to improve security
  secureApache()
  
  (adminUser,adminPassWd)=setupMediaWiki(settings={"enableUploads":True})
  
  print("Wiki Admin Username:"+adminUser)
  print("Wiki Admin password:"+adminPassWd)
if __name__ == "__main__":
 main()