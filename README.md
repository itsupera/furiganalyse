Furiganalyse
=============

Annotate Japanese ebooks (EPUB format) with furigana.

Setup and run
--------------

Using Docker to install all the dependencies and dictionaries (tested on Ubuntu 20.04):
```bash
docker build -t furiganalyse .
```

Run as a web app:
```bash
docker run -p 127.0.0.1:5000:5000 furiganalyse
```
Then open http://127.0.0.1:5000 in your web browser

Alternatively, can run it as a command line program:
```bash
# Run this from the directory your ebook (for example "book.epub") is in
docker run -v $PWD:/workspace --entrypoint=python3 furiganalyse -m furiganalyse /workspace/book.epub /workspace/book_with_furigana.epub
```