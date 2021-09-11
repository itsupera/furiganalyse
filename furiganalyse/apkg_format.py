import random
from typing import Iterator

import genanki

from furiganalyse.txt_format import iter_txt_lines


def generate_anki_deck(unzipped_input_fpath: str, deck_name: str, anki_deck_filepath: str):
    model_id = random.randrange(1 << 30, 1 << 31)
    model = genanki.Model(
        model_id,
        'Sentence cards (furiganalyse)',
        fields=[
            {'name': 'Sentence'},
            {'name': 'Word'},
            {'name': 'Definition'},
        ],
        templates=[
            {
                'name': 'Sentence to Word Definition',
                'qfmt': '{{Sentence}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Word}}<br>{{Definition}}',
            },
        ])

    deck_id = random.randrange(1 << 30, 1 << 31)
    description = 'Deck generated with <a href="https://github.com/itsupera/furiganalyse">furiganalyse</a><br/>' \
                  'If you can, please consider <a href="https://www.buymeacoffee.com/itsupera">donating</a> ' \
                  'to support my work, thank you !'
    deck = genanki.Deck(
        deck_id,
        deck_name,
        description
    )

    package = genanki.Package(deck)
    package.media_files = []

    idx = 0
    for line in iter_txt_lines(unzipped_input_fpath):
        for sentence in extract_sentences(line):
            note = genanki.Note(
                model=model,
                fields=[sentence, "", ""],
                due=idx,
            )
            deck.add_note(note)
            idx += 1

    package.write_to_file(anki_deck_filepath)


def extract_sentences(line: str) -> Iterator[str]:
    sentences = line.split("。")
    for sentence in sentences:
        sentence = sentence.lstrip().rstrip()
        if sentence:
            yield sentence