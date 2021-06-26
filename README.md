Furiganalyse
=============

Annotate Japanese ebooks (EPUB format) with furigana.

Setup and run
--------------

Using Docker (tested on Ubuntu 20.04):
```bash
docker build -t furiganalyse .
# From the directory your ebook is in
docker run -v $PWD:/workspace furiganalyse /workspace/book.epub /workspace/book_with_furigana.epub
```