<span class="badge-buymeacoffee">
<a href="https://www.buymeacoffee.com/itsupera" title="Donate to this project using Buy Me A Coffee"><img src="https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg" alt="Buy Me A Coffee donate button" /></a>
</span>
<span class="badge-dockercloudbuild">
<img src="https://img.shields.io/docker/cloud/build/itsupera/furiganalyse" title="Docker Cloud build status"></img>
</span>

Furiganalyse
=============

Annotate Japanese ebooks with furigana, and other conversions.

<a href="http://furiganalyse.itsupera.co/"><b>→ Try it here!</b></a>

![](assets/furiganalyse.jpg)

---

Supported input formats:
- EPUB
- AZW3 (without DRM)
- MOBI

Supported output formats:
- EPUB
- AZW3 (without DRM)
- MOBI
- Many text files (one per book part)
- Single text file
- Anki Deck (each sentence as a card)
- HTML (readable in web browser)

Setup and run
--------------

Using Docker to install all the dependencies and dictionaries (tested on Ubuntu 20.04):
```bash
docker build -t furiganalyse .
```
Or grab the latest prebuilt image:
```bash
docker pull itsupera/furiganalyse:latest
docker tag itsupera/furiganalyse:latest furiganalyse:latest
```

### Run as a web app
```bash
docker run -p 127.0.0.1:5000:5000 furiganalyse:latest
```
Then open http://127.0.0.1:5000 in your web browser

### Run as a CLI
```bash
# Run this from the directory your ebook (for example "book.epub") is in
docker run -v $PWD:/workspace --entrypoint=python3 furiganalyse:latest \
    -m furiganalyse /workspace/book.epub /workspace/book_with_furigana.epub
```