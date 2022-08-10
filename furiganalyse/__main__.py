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
from furiganalyse.params import FuriganaMode, OutputFormat, WritingMode
from furiganalyse.txt_format import write_txt_archive, concat_txt_files

logging.basicConfig(level=logging.INFO)

SUPPORTED_INPUT_EXTS = {".epub", ".azw3", ".mobi"}

def main(
    inputfile: str,
    outputfile: str,
    furigana_mode: FuriganaMode = FuriganaMode.add,
    output_format: OutputFormat = OutputFormat.epub,
    writing_mode: Optional[WritingMode] = None,
):
    with TemporaryDirectory() as td:
        filename, ext = os.path.splitext(os.path.basename(inputfile))
        if ext != ".epub":
            if ext in  SUPPORTED_INPUT_EXTS:
                logging.info(f"Convert {ext.lstrip('.').upper()} to EPUB first ...")
                tmpfilepath = os.path.join(td, "tmp.epub")
                capybre.convert(inputfile, tmpfilepath, as_ext='epub', suppress_output=False)
                inputfile = tmpfilepath
            else:
                raise Exception(f"Extension {ext} is not supported, input file format must be one of these: "
                                f"{','.join(SUPPORTED_INPUT_EXTS)}")

        unzipped_input_fpath = os.path.join(td, "unzipped")

        logging.info("Extracting the archive ...")
        with zipfile.ZipFile(inputfile, 'r') as zip_ref:
            zip_ref.extractall(unzipped_input_fpath)

        logging.info("Processing the files ...")
        process_epub_file(unzipped_input_fpath, furigana_mode, writing_mode, output_format)

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


if __name__ == '__main__':
    typer.run(main)
