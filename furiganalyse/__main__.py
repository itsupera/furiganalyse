import logging
import os
import zipfile
from tempfile import TemporaryDirectory
from typing import Optional

import capybre
import pypandoc
import typer

from furiganalyse.apkg_format import generate_anki_deck
from furiganalyse.epub_format import process_epub_file, write_epub_archive
from furiganalyse.known_words import load_word_list, load_word_list_from_path
from furiganalyse.params import FuriganaMode, OutputFormat, WritingMode
from furiganalyse.txt_format import write_txt_archive, concat_txt_files

logging.basicConfig(level=logging.INFO)

SUPPORTED_INPUT_EXTS = {".epub", ".azw3", ".mobi", ".txt", ".html"}

def main(
    inputfile: str,
    outputfile: str,
    furigana_mode: FuriganaMode = FuriganaMode.add,
    output_format: OutputFormat = OutputFormat.epub,
    writing_mode: Optional[WritingMode] = None,
    known_words_list: Optional[str] = None,
    custom_word_list_path: Optional[str] = None,
):
    # Load the known words list if specified (custom path takes precedence)
    exclude_words = None
    if custom_word_list_path:
        logging.info("Loading custom word list from: %s", custom_word_list_path)
        exclude_words = load_word_list_from_path(custom_word_list_path)
    elif known_words_list:
        logging.info("Loading known words list: %s", known_words_list)
        exclude_words = load_word_list(known_words_list)

    with TemporaryDirectory() as td:
        filename, ext = os.path.splitext(os.path.basename(inputfile))
        inputfile = convert_inputfile_if_not_epub(inputfile, ext, td)

        unzipped_input_fpath = os.path.join(td, "unzipped")

        logging.info("Extracting the archive ...")
        with zipfile.ZipFile(inputfile, 'r') as zip_ref:
            zip_ref.extractall(unzipped_input_fpath)

        logging.info("Processing the files ...")
        process_epub_file(
            unzipped_input_fpath, furigana_mode, writing_mode, output_format, exclude_words
        )

        logging.info("Creating the output file ...")
        if output_format == OutputFormat.epub:
            write_epub_archive(unzipped_input_fpath, outputfile)
        elif output_format in {OutputFormat.mobi, OutputFormat.azw3}:
            tmpfilepath = os.path.join(td, "tmp.epub")
            write_epub_archive(unzipped_input_fpath, tmpfilepath)
            capybre.convert(tmpfilepath, outputfile, as_ext=output_format.value, suppress_output=False)
        elif output_format == OutputFormat.many_txt:
            write_txt_archive(unzipped_input_fpath, outputfile)
        elif output_format == OutputFormat.single_txt:
            concat_txt_files(unzipped_input_fpath, outputfile)
        elif output_format == OutputFormat.apkg:
            deck_name = filename
            generate_anki_deck(unzipped_input_fpath, deck_name, outputfile)
        elif output_format == OutputFormat.html:
            tmpfilepath = os.path.join(td, "tmp.epub")
            write_epub_archive(unzipped_input_fpath, tmpfilepath)
            pypandoc.convert_file(tmpfilepath, 'html', outputfile=outputfile)
        else:
            raise ValueError("Invalid writing mode")


def convert_inputfile_if_not_epub(inputfile, ext, td):
    """
    Convert the input file to EPUB if it's not already in that format
    :param inputfile: file path to the input file
    :param ext: extension of the input file (e.g. ".html")
    :param td: temporary directory path to store the converted file
    :return: path to the converted file, or the original file if it's already in EPUB format
    """
    if ext not in SUPPORTED_INPUT_EXTS:
        raise Exception(f"Extension {ext} is not supported, input file format must be one of these: "
                        f"{','.join(SUPPORTED_INPUT_EXTS)}")

    if ext == ".epub":
        return inputfile

    logging.info(f"Convert {ext.lstrip('.').upper()} to EPUB first ...")
    tmpfilepath = os.path.join(td, "tmp.epub")
    if ext == ".html":
        pypandoc.convert_file(inputfile, 'epub', outputfile=tmpfilepath)
    else:
        capybre.convert(inputfile, tmpfilepath, as_ext='epub', suppress_output=False)
    return tmpfilepath


if __name__ == '__main__':
    typer.run(main)
