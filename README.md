<span class="badge-buymeacoffee">
<a href="https://www.buymeacoffee.com/itsupera" title="Donate to this project using Buy Me A Coffee"><img src="https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg" alt="Buy Me A Coffee donate button" /></a>
</span>
<span class="badge-dockercloudbuild">
<img src="https://img.shields.io/docker/cloud/build/itsupera/furiganalyse" title="Docker Cloud build status"></img>
</span>

Furiganalyse
=============

Annotate Japanese ebooks (EPUB format) with furigana.

Try it <a href="http://furiganalyse.itsupera.co/">here</a> !

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