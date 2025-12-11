FROM python:3.14.2-slim

# Bring in our code to the container
COPY xcel_itron2mqtt /opt/xcel_itron2mqtt
WORKDIR /opt/xcel_itron2mqtt
RUN pip3 install -r requirements.txt

ENTRYPOINT [ "/opt/xcel_itron2mqtt/run.sh" ]
