#!/bin/bash
#Builds docker image and runs container

if [ $1 = 'build' ]
then
  docker build -t nagios-g2n .
elif [ $1 = 'run' ]
then
  docker run -d --rm --name nagios -p 0.0.0.0:8080:80 -e NAGIOSADMIN_USER="icmAdmin" -e NAGIOSADMIN_PASS="icmAdmin" --mount source=nag_etc,target=/opt/nagios/etc --mount source=nag_libexec,target=/opt/nagios/libexec -d nagios-g2n
fi

