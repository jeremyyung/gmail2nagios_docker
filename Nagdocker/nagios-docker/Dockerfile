FROM manios/nagios
RUN apk add python3

WORKDIR /opt/pifiles
RUN git clone https://github.com/jeremyyung/gmail2nagios_docker.git
WORKDIR /opt/pifiles/gmail2nagios_docker/Nagios_configmgr/src
RUN cp hostpoll.py /opt/nagios/libexec
RUN mkdir /opt/nagios/pyfiles
RUN cp nagmanager.* nobjtemplates.cfg /opt/nagios/pyfiles
WORKDIR /opt/nagios/pyfiles

#REMEMBER TO SET THE $G2N_FILE environment variable
RUN sed -i 's/nagios_dir = .*/nagios_dir = \/opt\/nagios/g' /opt/nagios/pyfiles/nagmanager.cfg
RUN sed -i 's/g2n_file = .*/g2n_file = \/opt\/g2nout\/g2n.json/g' /opt/nagios/pyfiles/nagmanager.cfg

#Main script used by nagios checks, must be executable
RUN chmod +x /opt/nagios/libexec/hostpoll.py

#Copy over cfg files to (1)grant icmAdmin nagios permissions (2) let nagios send emails using my api key (change later)
COPY cgi.cfg /opt/nagios/etc/cgi.cfg
COPY ssmtp.conf /etc/ssmtp/ssmtp.conf
