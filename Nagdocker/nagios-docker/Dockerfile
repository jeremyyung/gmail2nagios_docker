FROM manios/nagios
RUN apk add python3

WORKDIR /opt/pifiles
RUN git clone https://github.com/jeremyyung/gmail2nagios_docker.git
WORKDIR /opt/pifiles/gmail2nagios_docker/Nagios_configmgr/src
RUN cp hostpoll.py /opt/nagios/libexec
RUN mkdir /opt/nagios/pyfiles
RUN cp nagmanager.* nobjtemplates.cfg /opt/nagios/pyfiles

#REMEMBER TO SET THE $G2N_FILE environment variable
RUN sed -i 's/nagios_dir = .*/nagios_dir = \/opt\/nagios/g' /opt/nagios/pyfiles/nagmanager.cfg
RUN sed -i 's/g2n_file = .*/g2n_file = \/tmp\/g2n.json/g' /opt/nagios/pyfiles/nagmanager.cfg
