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

import os, time, sys
from ruamel.yaml import YAML
from threading import Thread
import asn1tools

from Networking.networking import UDP_NET

# initialize errors
error = False

# test scripts should always print
printData = True

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
    error = True
    print("Unable to import yaml configs")
    raise e

netTestType = sys.argv[1]
if sys.argv[1] == "vanet":
    netTestType="VANET"
elif sys.argv[1] =="lan":
    netTestType="LAN"
else:
    print("invalid network test type......exiting")
    error = True

SPECIFICATION = '''
MyUserName DEFINITIONS ::= BEGIN
    Message ::= SEQUENCE {
        number      INTEGER,
        text        UTF8String
    }
END
'''
myUName = asn1tools.compile_string(SPECIFICATION,'uper')
uName = str(os.getlogin())
msg = {'number': 22, 'text': uName}
encoded = myUName.encode('Message', msg)


# Instantiate networks
# LAN
if netTestType=="LAN":
    try:
        lan = UDP_NET(CONFIG_FILE='LAN_params.yaml')
    except:
        error = True
    try:
        lan.start_connection()
    except:
        if printData:
            print("Not connected to a LAN interface")
            
# VANET
if netTestType=="VANET":
    try:
        vanet = UDP_NET(CONFIG_FILE='VANET_params.yaml')
    except:
        error = True
    try:
        vanet.start_connection()
    except:
        if printData:
            print("Not connected to a VANET interface")

def sendVANET(vPacket):
    global vanet
    vanet.send_data(vPacket)

def sendLAN(vPacket):
    global lan
    lan.send_data(vPacket)

def VANET_listening_thread():
    global error
    global myUName
    global uName

    while not error and not vanet.error:

        try:
            pkt = vanet.recv_packets()

            if pkt:
                print(myUName.decode('Message',pkt[0]))
                sendVANET(pkt[0])
        except:
            if printData:
                print("Waiting to configure LAN")
            time.sleep(0.25)
        time.sleep(loopTime)

    error = True

def LAN_listening_thread():
    global error

    while not error and not lan.error:
        try:
            pkt = lan.recv_packets()
            if pkt:
                if not parseLANPacket:
                    sendLAN(pkt)
                else:
                    # feature to parse incoming LAN packet is not enabled
                    # this feature may be used for things like responding to requests from the LAN connection, etc.
                    # there is no intent for this feature to be enabled but it is being allocated space in the code
                    raise NotImplementedError
        except:
            if printData:
                print("Waiting to configure VANET")
            time.sleep(0.25)
        time.sleep(loopTime)

    error = True

def main():

    global error

    # set up threads
    threads = []
    
    if netTestType=="LAN":
        LAN_mt = Thread(target= LAN_listening_thread)
        threads.append(LAN_mt)
    elif netTestType=="VANET":
        VANET_mt = Thread(target= VANET_listening_thread)
        threads.append(VANET_mt)

    for thread in threads:
        thread.daemon=True
        thread.start()
        time.sleep(0.2)

    try:
        while not error:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard Interrupt Occurred")
    finally:
        error = True
       
# code starts here
if __name__ == '__main__':

    # print to terminal that V2X radio is starting up
    print("----------------------------------------------------\nSTARTING V2X RADIO\n----------------------------------------------------")
    
    main()
