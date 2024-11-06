#!/usr/bin/env python3

# Written by the USDOT Volpe National Transportation Systems Center
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.


import os, logging, time
from ruamel.yaml import YAML
from threading import Thread, Lock
from pathlib import Path, PurePath
import argparse
from binascii import unhexlify

from Networking.networking import UDP_NET

# Initialize mutex
mutex = Lock()

# Initialize argpaser
parser = argparse.ArgumentParser()
parser.add_argument("-p", "--print", help="prints output to the terminal", action="store_true")
args = parser.parse_args()


# Logging
v2x_logger = None
LOGGING_LEVEL = logging.INFO
logs_directory = PurePath.joinpath(Path.cwd(), "Logs")

# IF: Check if the Logs directory does not exist
if not os.path.exists(logs_directory):
	# Create Logs directory
	os.mkdir(logs_directory, 0o775)

# Setup logger with formatting
log_filename = "v2x_OBU.log"
v2x_logger = logging.getLogger(__name__)
v2x_logger.setLevel(LOGGING_LEVEL)
v2x_logger_handler = logging.FileHandler(os.path.join(logs_directory, log_filename), "w")
v2x_logger_handler.setLevel(LOGGING_LEVEL)
v2x_logger_formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s", datefmt= "%d-%b-%y %H:%M:%S")
v2x_logger_handler.setFormatter(v2x_logger_formatter)
v2x_logger.addHandler(v2x_logger_handler)
# Start logging
v2x_logger.info("\n---------------------------\nStarting V2X OBU Logger\n---------------------------")

# Initialize error
error = False

# Initialize waiting for ack
waiting_for_ack = False

# Sets printData bool to cmd line arg
printData = args.print

# Import Configs
script_dir = os.path.dirname(__file__)
fpath = 'config/params.yaml'
file_path = os.path.join(script_dir, fpath)
try:
	y = YAML(typ='safe')
	with open(file_path,'r') as f:
		params = y.load(f)
	parseLANPacket = params['LAN_DECODE']
	parseVANETPacket = params['VANET_DECODE']
	radioApps = params['RADIO_APPS']
	printData = params['print_data']
	loopTime = params['loop_time']
	logLevel = params['logging_level']
except Exception as e:
	v2x_logger.error("Unable to import master yaml configs")
	error = True
	print("Unable to import yaml configs")
	raise e

if logLevel == 'DEBUG': v2x_logger.setLevel(logging.DEBUG)
elif logLevel == 'INFO': v2x_logger.setLevel(logging.INFO)
elif logLevel == 'ERROR': v2x_logger.setLevel(logging.ERROR)
elif logLevel == 'WARNING': v2x_logger.setLevel(logging.WARNING)
else: 
	v2x_logger.setLevel(logging.WARNING)
	print("Configured LOGGING LEVEL is invalid. Level is set to WARNING.")
	v2x_logger.warning("Configured LOGGING LEVEL is invalid. Level is set to WARNING.")


# Instantiate networks
# LAN
try:
	lan = UDP_NET(CONFIG_FILE='LAN_params.yaml',logger=v2x_logger)
except:
	error = True
try:
	lan.start_connection()
except:
	v2x_logger.warning("Not connected to a LAN interface")
	if printData:
		print("Not connected to a LAN interface")

# VANET
try:
	vanet = UDP_NET(CONFIG_FILE='VANET_params.yaml',logger=v2x_logger)
except:
	error = True
try:
	vanet.start_connection()
except:
	v2x_logger.warning("Not connected to a VANET interface")
	if printData:
		print("Not connected to a VANET interface")

def sendVANET(vPacket):
	global vanet
	vanet.send_data(vPacket)

def sendLAN(lPacket):
	global lan
	lan.send_data(strip_header(lPacket))

def VANET_listening_thread():
	global error, waiting_for_ack
	previous_packet_received = ""
	ack = b"1"
	while not vanet.error:
		with mutex:
			if error:
				break

		try:
			pkt = vanet.recv_packets()
			v2x_logger.debug("Received %s from VANET", pkt)
			if pkt:
				if not parseVANETPacket:
					# Check if ack or payload
					data = pkt[0].decode('utf-8')
					if data == "1":  # Ack
						with mutex:
							waiting_for_ack = False
						v2x_logger.info("Received ack")
					elif data == previous_packet_received:  # Duplicate message received, so just resend ack
						sendVANET(ack)
						v2x_logger.info("Received duplicate message, resending ack")
					else:  # New message received, forward it to LAN and send ack
						sendVANET(ack)
						sendLAN(pkt[0])
						previous_packet_received = pkt[0]
						v2x_logger.info("Received new message, sent ack")
				else:
					# feature to parse incoming VANET message is not yet enabled
					v2x_logger.error("Feature to parse incoming VANET message is not yet enabled")
					raise NotImplementedError
				if printData:
					print(pkt)
		except:
			if printData:
				print("Waiting to configure LAN")
			v2x_logger.info("Waiting to configure LAN")
			time.sleep(0.25)
		time.sleep(loopTime)

	with mutex:
		error = True
		v2x_logger.info("Terminating VANET Thread")

def LAN_listening_thread():
	global error, waiting_for_ack

	while not lan.error:
		with mutex:
			if error:
				v2x_logger.info("Terminating LAN Thread")
				break

		try:
			pkt = lan.recv_packets()
			if pkt:
				if not parseLANPacket:
					sendVANET(pkt[0])
					# Wait for ack
					waiting_for_ack = True
					v2x_logger.info("Message sent, waiting for ack")
					time.sleep(1.0)
					for i in range(120):  # Attempt to rebroadcast for 2 minutes before giving up
						with mutex:
							if waiting_for_ack:
								sendVANET(pkt[0])
								v2x_logger.info("Still waiting for ack")
							else:
								break
						time.sleep(1.0)
					if waiting_for_ack:
						raise Exception("Ack was never received")
				else:
					# feature to parse incoming LAN packet is not enabled
					# this feature may be used for things like responding to requests from the LAN connection, etc.
					# there is no intent for this feature to be enabled but it is being allocated space in the code
					v2x_logger.error("Feature to parse incoming LAN is not enabled")
					raise NotImplementedError
		except:
			if printData:
				print("Waiting to configure VANET")
			v2x_logger.debug("Waiting to configure VANET")
			time.sleep(0.25)
		time.sleep(loopTime)

	with mutex:
		error = True
		v2x_logger.info("Terminating LAN Thread")

# Removes unnecessary RSU header information
# Source: https://github.com/usdot-fhwa-stol/carma-platform/blob/develop/engineering_tools/msgIntersect.py
def strip_header(packet):
    data = packet.decode('ascii')
    idx = data.find("Payload=")
    payload = data[idx+8:-1]
    encoded = payload.encode('utf-8')
    return unhexlify(encoded)

def main():

	global error

	# set up threads
	threads = []

	LAN_mt = Thread(target= LAN_listening_thread)
	VANET_mt = Thread(target= VANET_listening_thread)

	threads.append(LAN_mt)
	threads.append(VANET_mt)

	for thread in threads:
		v2x_logger.debug("Starting %s", thread.name)
		thread.daemon=True
		thread.start()
		time.sleep(0.2)
	v2x_logger.debug("All Threads Started")

	try:
		while not error:
			time.sleep(1)
	except KeyboardInterrupt:
		v2x_logger.critical("Keyboard Interrupt Occurred")
	finally:
		error = True
		v2x_logger.critical("\n---------------------------\nTerminating V2X OBU Logger\n---------------------------")

# code starts here
if __name__ == '__main__':

	# print to terminal that V2X radio is starting up
	print("----------------------------------------------------\nSTARTING V2X RADIO\n----------------------------------------------------")
	
	main()
