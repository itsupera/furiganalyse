# Use a base that provides mecab and the dictionary, and which is regularly updated:
# https://hub.docker.com/r/intimatemerger/mecab-ipadic-neologd
FROM intimatemerger/mecab-ipadic-neologd:latest3

MAINTAINER Itsupera <itsupera@gmail.com>

# Need git to pull some of the dependencies
RUN apk add git

# Setup our dependencies
WORKDIR /workdir
ADD setup.py .
ADD setup.cfg .
# Little optimization in order to install our dependencies before copying the source
RUN mkdir furiganalyse
RUN pip3 install -e .

# Add the sources
ADD furiganalyse furiganalyse

# ENTRYPOINT ["python3", "-m", "furiganalyse"]
ENTRYPOINT ["python3", "-m", "furiganalyse.app"]