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

# This code creates a socket based on inputted variables, enables logging, and allows for sending/receiving

import os, logging
from ruamel.yaml import YAML
import socket
import netifaces as ni

class UDP_NET:

	def __init__(self, CONFIG_FILE='VANET_params.yaml', logging_level=logging.DEBUG, print_data=False, logger=None):

		self.print_data = print_data

		self.error = False

		self.netType = CONFIG_FILE.split('_')[0]

		# Logging
		# If no logger creates log directory
		if logger:
			self.logger = logger
		else:
			logs_directory = os.path.join(os.getcwd(), "Logs")

			# IF: Check if the Logs directory does not exist
			if not os.path.exists(logs_directory):
				# Create Logs directory
				os.mkdir(logs_directory, 0o777)

			# Log filename
			log_filename = "Network_{}.log".format(self.netType)

			# Initialize logger
			self.logger = logging.getLogger(__name__)
			self.logger.setLevel(logging_level)

			logger_handler = logging.FileHandler(os.path.join(logs_directory, log_filename), "w")
			logger_handler.setLevel(logging_level)

			logger_formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s", datefmt= "%d-%b-%y %H:%M:%S")

			logger_handler.setFormatter(logger_formatter)
			self.logger.addHandler(logger_handler)

		# Import Configs
		script_dir = os.path.dirname(__file__)
		fpath = 'config/' + CONFIG_FILE
		file_path = os.path.join(script_dir, fpath)
		try:
			y=YAML(typ='safe')
			with open(file_path,'r') as f:
				params = y.load(f)
			self.sendIP = params['sendIP']
			self.sendPORT = params['sendPORT']
			self.recvIP = params['recvIP']
			self.recvPORT = params['recvPORT']
			self.bufferSize = params['BUFFER_SIZE']
			INTERFACE = params['INTERFACE']
		except Exception as e:
			if logger:
				self.logger.error("{}: Unable to import yaml configs".format(self.netType))
				self.error = True
				raise e
			if self.print_data:
				print("Unable to import yaml configs")

		try:
			self.selfIP = ni.ifaddresses(INTERFACE)[ni.AF_INET][0]['addr']
		except:
			self.logger.warning("Not connected to the {} interface".format(self.netType))
			if print_data:
				print("Not connected to the {} interface".format(self.netType))
				raise e

		# Initialize socket to None
		self.sock=None

		# Log initial data
		self.logger.info("{}: HARDWARE INTERFACE: {}".format(self.netType, INTERFACE))
		self.logger.info("{}: SEND IP | PORT: {} | {}".format(self.netType,self.sendIP,self.sendPORT))
		self.logger.info("{}: RECV IP | PORT: {} | {}".format(self.netType,self.recvIP, self.recvPORT))

	def start_connection(self):
		# Attempts to create a bound socket to the target IP:PORT
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			self.sock.bind((self.recvIP, self.recvPORT))
			self.logger.info("{}: Socket bound at: {} | {}".format(self.netType,self.recvIP,self.recvPORT))
		except Exception as excep:
			self.logger.critical("{}: Unable to bind socket".format(self.netType))
			self.error=True

			if self.print_data:
				print(type(excep))
				print(excep.args)
				print("{}: Unable to bind socket".format(self.netType))
			raise NotImplementedError

	def send_data(self, packet, encoded_status = True):
		# Attempts to encode and send a packet to the target IP:PORT
		try: 
			if not encoded_status:
				self.logger.debug("{}: Packet encoded as type 'ascii'".format(self.netType))
				packet = str(packet).encode('ascii')
			self.sock.sendto(packet,(self.sendIP,self.sendPORT))
			self.logger.info("{}: Packet '{}' sent to {}".format(self.netType,packet,self.sendIP))
		except:
			self.logger.warning("Attempted to send message to the {} - it may not yet be connected".format(self.netType))
			if self.print_data:
				print("{} may not yet be connected".format(self.netType))

	def recv_packets(self):
		# Attempts to retrieve packets from the current packet buffer
		try:
			packet = self.sock.recvfrom(self.bufferSize)
			# checks if received packet is from self
			if packet[1][0] != self.selfIP:
				self.logger.info("{}: Received '{}' from {}".format(self.netType, packet[0], packet[1][0]))
				return packet
			else:
				self.logger.debug("{}: Received packet from self @ IP: {}".format(self.netType,packet[1][0]))
				return None
		except:
			self.logger.warning("Attempted to receive message from the {} - it may not yet be connected".format(self.netType))
			if self.print_data:
				print("Network may not yet be connected")
			return None
