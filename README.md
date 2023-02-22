# Connect Your Smart Meter to MQTT!

Recently Xcel energy rolled out smart meter installations to facilitate TOU(Time of Use) pricing. This also benefits us, the users, as it provides us with a free way to see how much energy we're using at any time. This repo will help you get up and running with a python program that will query your meter on your network and convert its readings to MQTT messages.

## Setup

Enroll in Xcel enery launchpad and get your meter joined to your network.\
Generate an SSL key to use to provide a handshake to your meter, and add this to your Xcel launchpad 

## Docker

Build the container.
```
./docker/build.sh
```
Run the container. The easiest way currently to pass through mDNS to the container is to use host networking.

 Maybe in the future use https://github.com/flungo-docker/avahi
```
docker run --rm \
    --net host \
    -e CERT_PATH=/path/to/certfile \
    -e KEYPATH=/path/to/certfile \
    -v /path/to/persistent/data:/data \
    xcel_itron2mqtt:latest
```

For running as a developer, the following is helpful to allow you to work in the container
```
docker run --rm -it \
    --net host \
    -v `pwd`:/data \
    --entrypoint /bin/sh \
    xcel_itron2mqtt:latest
```
## Contributing

Create a new branch and pull request once your new feature/fix is complete

# Contact
Zak Nye - [zaknye.com](https://zaknye.com) - zaknye@gmail.com