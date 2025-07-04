FROM python:3.12-bookworm
LABEL org.opencontainers.image.authors="itsupera@gmail.com"

# switch to root user to use apt-get
USER root

# Install mecab and mecab-ipadic from Debian packages
RUN apt-get update && apt-get install -y \
  git curl file python3-poetry \
  mecab=0.996-14+b14 mecab-ipadic=2.7.0-20070801+main-3 mecab-ipadic-utf8=2.7.0-20070801+main-3 libmecab-dev=0.996-14+b14 \
  sudo \
  pandoc calibre \
  && rm -rf /var/lib/apt/lists/*

# NEologd
RUN git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git
RUN cd mecab-ipadic-neologd && ./bin/install-mecab-ipadic-neologd -n -a -y
RUN rm -rf mecab-ipadic-neologd

# Move config file from /etc/mecabrc (default install path on Debian) to what the program expects
# Setup MeCab to use mecab-ipadic-neologd dict by default
RUN cp /etc/mecabrc /usr/local/etc/mecabrc && \
  sed -i "s'^dicdir.*'dicdir = /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd'g" /usr/local/etc/mecabrc

# Setup our dependencies
WORKDIR /workdir
ADD README.md .
ADD pyproject.toml .
ADD poetry.lock .
# Little optimization in order to install our dependencies before copying the source
RUN mkdir furiganalyse && touch furiganalyse/__init__.py
RUN pip3 install -e .

# Add the sources
ADD furiganalyse furiganalyse
ADD assets assets

EXPOSE 5000

ENTRYPOINT ["uvicorn", "furiganalyse.app:app", "--workers", "10", "--host", "0.0.0.0", "--port", "5000"]
