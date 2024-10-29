# CARMA 1tenth Vehicle to Everything

v2x-emulator is a new repository that enables Raspberry Pi’s to act as mock Onboard Units (OBUs) and Roadside Units (RSUs) for the CDA1tenth platform. This includes the ability to communicate with vehicles and V2X Hub instances, as well as forwarding messages over WiFi to other Raspberry Pi’s. This repo provides code for the CDA1tenth Vehicle to Everything (V2X) radio emulator on a Raspberry Pi 4B+.

## Python requirements
This package requires the following three python packages:
- [netifaces](https://pypi.org/project/netifaces/)
- [ruamel.yaml](https://pypi.org/project/ruamel.yaml/)
- [asn1tools](https://pypi.org/project/asn1tools/)

These packages can be installed by navigating to the V2X directory, and running:
```
sudo pip install -r ./requirements.txt
```

## Functionality
The V2X radios function similar to the DSRC radios used by CARMA Platform equipped vehicles in that they receive UDP packets from a PC and broadcast them "over the air." The radios used by the CARMA Platform are configured to be in Road Side Unit (RSU) mode where messages are forwarded, and V2X seeks to emulate this behavior.

The V2X radios are intended to use the same driver as the full-scale CARMA vehicle's DSRC radios, specifically the [carma-cohda-dsrc-driver](https://github.com/usdot-fhwa-stol/carma-cohda-dsrc-driver).

The V2X solution uses the WiFi band for its Vehicle Area Network (VANET) rather than Dedicated Short Range Communications (DSRC) or Cellular V2X (C-V2X). It is intended to be an educational tool used to facilitate communication and cooperation between scaled-down vehicles and infrastructure - and it not intended as a deployable solution. Public Deployment of a WiFi-based VANET is outside of the scope of the CDA1tenth project, and may be susceptible to restrictions/guidelines from the Federal Communications Commission (FCC).

V2X radios are capable of running their own applications through threading - provided that message decoding/encoding and parsing is enabled.
At this time, the radios do not decode or encode packets and function only to forward messages - similar to the full scale CARMA Platform vehicles' radios. However, further work can be done to enable this.

At a high level, the V2X radios can:
- Receive UDP packets over the LAN from the Jetson Xavier
- Broadcast UDP packets over the VANET to other scaled-down cooperative entities
- Receive UDP packets over the VANET from other scaled-down cooperative entities
- Broadcast UDP packets over the LAN to the Jetson Xavier

Broadcasting over WiFi for the VANET allows for each V2X radio to receive its own messages that it broadcasts. The V2X radio checks the IP of the device that sends each message, and filters out messages that are sent from its own IP.

## Configuration
The V2X radios are connected to both a local area network (the connection between the Pi and a Jetson Xavier NX with a crossover ethernet cable) and a wireless network (the VANET).

The radios should be configured to work on each network by adjusting the parameters in the following two YAML files:
1. `./src/Networking/config/LAN_params.yaml`
2. `./src/Networking/config/VANET_params.yaml`

The IP, Port, and Network interface for each network must be set correctly. The IP and Port that are used for the LAN network should relate to the IP and Port in the ROS2 driver's params.yaml and dsrc.cfg files from the `carma-cohda-dsrc-driver` package.

If the wireless and wired network interfaces are unknown, the following command will identify the available network interfaces:
```
basename -a /sys/class/net/*
```

The VANET IP and Port that are used should be consistent across all radios on the VANET.

## Testing
You can test a full loop of the VANET with the scripts broadcaster.py and returner.py

Configure the parameter YAML files on two machines and:
- on one machine, run:
```
python broadcaster.py vanet
```
- on the other machine, run:
```
python returner.py vanet
```

The broadcaster will create an uper encoded asn.1 message and broadcast it over the vanet.

The returner will receive the message, and send the message back over the vanet.

The broadcaster will receive the message, and it will compare the received copy against the originally broadcasted copy.

## Running
Once all config files are correctly made, run the `V2X_OBU.py` script to start the on board unit (OBU) emulator. This can be run on boot automatically with a crontab job

```
ln -s /home/$USER/cda_ws/src/v2x-emulator/src/V2X_OBU.py /bin/V2X_OBU.py
crontab -e
# Add this line to the end
@reboot python /bin/V2X_OBU.py &
```

## Contribution
Welcome to the CARMA contributing guide. Please read this guide to learn about our development process, how to propose pull requests and improvements, and how to build and test your changes to this project. [CARMA Contributing Guide](https://github.com/usdot-fhwa-stol/carma-platform/blob/develop/Contributing.md) 

## Code of Conduct 
Please read our [CARMA Code of Conduct](https://github.com/usdot-fhwa-stol/carma-platform/blob/develop/Code_of_Conduct.md) which outlines our expectations for participants within the CARMA community, as well as steps to reporting unacceptable behavior. We are committed to providing a welcoming and inspiring community for all and expect our code of conduct to be honored. Anyone who violates this code of conduct may be banned from the community.

## Attribution
The development team would like to acknowledge the people who have made direct contributions to the design and code in this repository. [CARMA Attribution](https://github.com/usdot-fhwa-stol/carma-platform/blob/develop/ATTRIBUTION.txt) 

## License
By contributing to the Federal Highway Administration (FHWA) Connected Automated Research Mobility Applications (CARMA), you agree that your contributions will be licensed under its Apache License 2.0 license. [CARMA License](https://github.com/usdot-fhwa-stol/carma-platform/blob/develop/docs/License.md) 

## Contact
Please click on the CARMA logo below to visit the Federal Highway Adminstration(FHWA) CARMA website. For technical support from the CARMA team, please contact the CARMA help desk at CAVSupportServices@dot.gov.

[![CARMA Image](https://raw.githubusercontent.com/usdot-fhwa-stol/carma-platform/develop/docs/image/CARMA_icon.png)](https://highways.dot.gov/research/research-programs/operations/CARMA)
