From centos8:base

#Install fresh cron daemon
RUN yum install -y git crontabs cronie && rm -rf /etc/cron.*/*

#Git clones latest gmail2nag source files
WORKDIR /opt
RUN mkdir /opt/g2nout
RUN git clone https://github.com/jeremyyung/gmail2nagios_docker.git
RUN chmod +x /opt/gmail2nagios_docker/Nagios_email_alerts/pymail2nag/src/gmail2nag.py

#Setup cronjob by copying over cronfile
COPY ./cronfile /etc/cron.d/cronfile
RUN chmod 0644 /etc/cron.d/cronfile && crontab /etc/cron.d/cronfile

COPY ./envecho.sh /opt/

#Starts crond in the foreground
#CMD ["crond","-n"]
CMD ["sh","-c","bash /opt/envecho.sh; crond -n"]

