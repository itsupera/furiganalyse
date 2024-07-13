FROM python:3.12-bookworm
LABEL org.opencontainers.image.authors="itsupera@gmail.com"

# switch to root user to use apt-get
USER root

RUN apt-get update && apt-get install -y \
  git curl file python3-poetry \
  && rm -rf /var/lib/apt/lists/*

# Install MeCab and Cabocha for extracting phonemes from sentence transcripts
# (Adapted from https://github.com/torao/ml-nlp/blob/master/ml-nlp-corpus/docker)

# MeCab 0.996
RUN curl -o mecab-0.996.tar.gz -L 'https://drive.google.com/uc?export=download&id=0B4y35FiV1wh7cENtOXlicTFaRUE'
RUN tar zxfv mecab-0.996.tar.gz
RUN cd mecab-0.996; ./configure; make; make check; make install
RUN ldconfig
RUN rm -rf mecab-0.996 mecab-0.996.tar.gz

# MeCab IPADIC
RUN curl -o mecab-ipadic-2.7.0-20070801.tar.gz -L 'https://drive.google.com/uc?export=download&id=0B4y35FiV1wh7MWVlSDBCSXZMTXM'
RUN tar zxf mecab-ipadic-2.7.0-20070801.tar.gz
RUN cd mecab-ipadic-2.7.0-20070801 && ./configure --with-charset=utf8 && make && make install
RUN rm -rf mecab-ipadic-2.7.0-20070801 mecab-ipadic-2.7.0-20070801.tar.gz

# NEologd
RUN git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git
RUN cd mecab-ipadic-neologd && ./bin/install-mecab-ipadic-neologd -n -a -y
RUN rm -rf mecab-ipadic-neologd

# Setup MeCab to use mecab-ipadic-neologd dict by default
RUN sed -i "s'^dicdir.*'dicdir = /usr/local/lib/mecab/dic/mecab-ipadic-neologd'g" /usr/local/etc/mecabrc

# Need pandoc for EPUB to HTML conversion, and Calibre for other ebook formats
RUN apt-get update && apt-get install -y \
  pandoc calibre \
  && rm -rf /var/lib/apt/lists/*

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