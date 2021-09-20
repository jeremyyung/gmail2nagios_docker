#!/bin/bash
#Builds docker image and runs container

if [ $1 = 'build' ]
then
  docker build --no-cache -t gmail2nag .
elif [ $1 = 'run' ]
then
  docker run --name g2n --rm -d --mount source=g2n_db,target=/opt/g2nout --env GM_URL=imap.gmail.com --env GM_MAILBOX_NAME=monitor_spam --env GM_MAIL_STATUS=UNSEEN --env GM_USERNAME=jeremy.yung@icmanage.com --env GM_API_PW=zeilvzlgjqiozsxx gmail2nag
fi

