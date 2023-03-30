FROM python:3.10-slim

# Bring in our code to the container
COPY xcel_itron2mqtt /opt/xcel_itron2mqtt
WORKDIR /opt/xcel_itron2mqtt
RUN pip3 install -r requirements.txt

# Add our unsafe SSL cert hack to PATH
ENV OPENSSL_CONF=/opt/xcel_itron2mqtt/openssl.conf
ENTRYPOINT [ "/opt/xcel_itron2mqtt/run.sh" ]