# Connect Your Smart Meter to MQTT!

Recently Xcel energy rolled out smart meter installations to facilitate TOU(Time of Use) pricing. This also benefits us, the users, as it provides us with a free way to see how much energy we're using at any time. This repo will help you get up and running with a python program that will query your meter on your network and convert its readings to MQTT messages.

## Setup

Enroll in Xcel enery launchpad and get your meter joined to your network.\
Generate an SSL key to use to provide a handshake to your meter, and add this to your Xcel launchpad 
```
./scripts/generate_keys.sh
```
This script will generate new keys and print out the LFDI string to use for registering with Xcel. If you're already generated keys and you need to retrieve the LFDI string again run:
```
./scripts/generate_keys.sh -p
```
These keys will be saved in the local directory `certs/.cert.pem` and `certs/.key.pem`

## Docker

Build the container.
```
./docker/build.sh
```
Then run the container using the required options below. 
### Options
The following are options that may be passed into the container in the form of environment variables or required volumes
| Option | Expected Arg | Optional | 
| ------ | ------------ | -------- |
| -v <path_to_cert_folder>:/opt/xcel_itron2mqtt/.certs | Folder path to the certs generated with the generate keys script | NO |
| -e MQTT_SERVER | IP address of the MQTT server to communicate with | NO |
| -e MQTT_PORT | Port # of the MQTT server to communicate with, **Default: 1883**| yes |
| -e CERT_PATH | Path to cert file (within the container) if different than the default | yes |
| -e KEY_PATH | Path to key file (within the container) if different than the default | yes |

### Example
```
docker run --rm -d \
    --net host \
    -e MQTT_SERVER=<IP_ADDRESS> \
    -v <path_to_cert_folder>:/opt/xcel_itron2mqtt/certs \
    xcel_itron2mqtt:latest
```
> The easiest way currently to pass through mDNS to the container is to use host networking.
>
> Maybe in the future use https://github.com/flungo-docker/avahi
### Development Example
For running as a developer, the following is helpful to allow you to work in the container
```
docker run --rm -it \
    --net host \
    -v `pwd`:/opt/xcel_itron2mqtt \
    --entrypoint /bin/sh \
    xcel_itron2mqtt:latest
```
## Contributing

Create a new branch and pull request once your new feature/fix is complete

# Contact
Zak Nye - [zaknye.com](https://zaknye.com) - zaknye@gmail.com