#!/bin/bash
dockerfile=docker/Dockerfile
docker build -t xcel_itron2mqtt -f ${dockerfile} .