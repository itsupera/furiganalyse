import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from enum import Enum
from tempfile import TemporaryDirectory
from typing import Tuple, List, Iterable, Optional

import typer
from furigana.furigana import create_furigana_html

logging.basicConfig(level=logging.INFO)

NAMESPACE = "{http://www.w3.org/1999/xhtml}"


class Mode(str, Enum):
    add = "add"
    replace = "replace"
    remove = "remove"


class OutputFormat(str, Enum):
    epub = "epub"
    txt = "txt"


class WritingMode(str, Enum):
    horizontal_tb = "horizontal-tb"
    vertical_rl = "vertical-rl"
    vertical_lr = "vertical-lr"


def main(
    inputfile: str,
    outputfile: str,
    mode: Mode = Mode.add,
    output_format: OutputFormat = OutputFormat.epub,
    writing_mode: Optional[WritingMode] = None,
):
    with TemporaryDirectory() as td:
        unzipped_input_fpath = os.path.join(td, "unzipped")

        logging.info("Extracting the archive ...")
        with zipfile.ZipFile(inputfile, 'r') as zip_ref:
            zip_ref.extractall(unzipped_input_fpath)

        logging.info("Processing the files ...")
        if writing_mode is not None:
            update_writing_mode(unzipped_input_fpath, writing_mode)

        for root, _, files in os.walk(unzipped_input_fpath):
            for file in files:
                if os.path.splitext(file)[1] in {".html", ".xhtml"}:
                    logging.info(f"    Processing {file}")
                    html_filepath = os.path.join(root, file)
                    tree = process_html(html_filepath, mode)
                    if output_format == OutputFormat.txt:
                        txt_outputfile = os.path.splitext(html_filepath)[0] + '.txt'
                        convert_html_to_txt(tree, txt_outputfile)
                    else:
                        tree.write(html_filepath, encoding="utf-8")

        logging.info("Creating the archive ...")
        if output_format == OutputFormat.epub:
            write_epub_archive(unzipped_input_fpath, outputfile)
        else:
            write_txt_archive(unzipped_input_fpath, outputfile)


def update_writing_mode(unzipped_input_fpath: str, writing_mode: WritingMode):
    css_filepath = os.path.join(unzipped_input_fpath, "stylesheet.css")
    with open(css_filepath) as fd:
        css_content = fd.read()

    pattern = re.compile(r"-webkit-writing-mode: [^;\n]+")
    css_content = pattern.sub(f"-webkit-writing-mode: {writing_mode}", css_content)

    with open(css_filepath, "w") as fd:
        fd.write(css_content)


def write_epub_archive(unzipped_input_fpath: str, outputfile: str):
    """
    Write the modified extracted EPUB archive to a new archive file.
    """
    with zipfile.ZipFile(outputfile, 'w') as zip_out:
        for folder_name, _, filenames in os.walk(unzipped_input_fpath):
            for filename in filenames:
                rel_dir = os.path.relpath(folder_name, unzipped_input_fpath)
                rel_file = os.path.join(rel_dir, filename)
                file_path = os.path.join(folder_name, filename)
                # Add file to zip
                zip_out.write(file_path, rel_file)
                logging.info(f"    Adding {rel_file}")


def write_txt_archive(unzipped_input_fpath: str, outputfile: str):
    """
    Only keep the converted txt files within the archive.
    """
    with zipfile.ZipFile(outputfile, 'w') as zip_out:
        for folder_name, _, filenames in os.walk(unzipped_input_fpath):
            for filename in filenames:
                extension = os.path.splitext(filename)[1]
                if extension == ".txt":
                    rel_dir = os.path.relpath(folder_name, unzipped_input_fpath)
                    rel_file = os.path.join(rel_dir, filename)
                    file_path = os.path.join(folder_name, filename)
                    # Add file to zip
                    zip_out.write(file_path, rel_file)
                    logging.info(f"    Adding {rel_file}")


def process_html(inputfile: str, mode: Mode) -> ET.ElementTree:
    tree = ET.parse(inputfile)
    process_tree(tree, mode)
    return tree


def process_tree(tree: ET.ElementTree, mode: Mode):
    parent_map = dict((c, p) for p in tree.iter() for c in p)

    if mode in {"remove", "replace"}:
        remove_existing_furigana(tree, parent_map)

    if mode in {"add", "replace"}:
        ps = tree.findall(f'.//{NAMESPACE}*')
        for p in ps:
            if not p.tag.endswith("rt"):
                logging.debug(f">>> BEFORE {p.tag} > '{p.text}' {list(p)} '{p.tail}'")
                process_head(p)
                process_tail(p, parent_map[p])
                logging.debug(f">>> AFTER  {p.tag} > '{p.text}' {list(p)} '{p.tail}'")

        # Add the namespace to our new elements
        elems = tree.findall('.//{}*')
        for elem in elems:
            elem.tag = NAMESPACE + elem.tag


def remove_existing_furigana(tree: ET.ElementTree, parent_map: dict):
    """
    Replace all existing ruby elements by their text, e.g., <ruby>X<rt>Y</rt></ruby> becomes X.
    """
    elems = tree.findall(f'.//{NAMESPACE}ruby')
    for elem in elems:
        # Remove all the <rt> children, e.g., the readings, but keep the text from other childs
        childs_text = []
        for child in list(elem):
            if not child.tag.endswith("rt") and not child.tag.endswith("rp"):
                text = (child.text or "") + (child.tail or "")
            else:
                text = child.tail or ""
            childs_text.append(text)
            elem.remove(child)

        # Replacing the node the its text, childs text and tail
        new_text = (elem.text or "") + "".join(childs_text) + (elem.tail or "")

        parent_elem = parent_map[elem]

        # Find the previous child to append our new text to it
        idx = list(parent_elem).index(elem)
        if idx == 0:
            # If our element was the first child, append to parent node's text
            parent_elem.text = (parent_elem.text or "") + new_text
        else:
            # Otherwise, append to the tail of previous children
            previous_elem = parent_elem[idx - 1]
            previous_elem.tail = (previous_elem.tail or "") + new_text

        # Finally, remove our ruby element from its parent
        parent_elem.remove(elem)


def process_head(elem: ET.Element):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.text or elem.tag.endswith("ruby"):
        return

    text = elem.text.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text)

        # Replace the original text by the ruby childs "head"
        elem.text = head

        # Insert the children at the beginning
        for child in reversed(children):
            elem.insert(0, child)


def process_tail(elem: ET.Element, parent_elem: ET.Element):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.tail:
        return

    text = elem.tail.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text)

        # Replace the original tail by the rubys "head"
        elem.tail = head

        # Insert the ruby children just after the element
        idx = list(parent_elem).index(elem)
        for child in reversed(children):
            parent_elem.insert(idx + 1, child)


def create_parsed_furigana_html(text: str) -> Tuple[str, List[ET.Element], str]:
    """
    Generate the furigana and return it parsed: "head" text, <ruby> children, "tail" text.
    """
    new_text = create_furigana_html(text)

    # Need to wrap the children <ruby> elements in something to parse them
    try:
        elem = ET.fromstring(f"""<p>{new_text}</p>""")
    except ET.ParseError:
        logging.error(f"XML parsing failed for {new_text}, which was generated from: {text}")
        raise

    # Return the parts that will need to be integrated in the XML tree
    return elem.text, list(elem), elem.tail


kanji_pattern = re.compile(f"[一-龯]")


def contains_kanji(text: str) -> bool:
    return bool(kanji_pattern.search(text))


def convert_html_to_txt(tree, outputfile):
    with open(outputfile, "w") as fd:
        for line in convert_html_to_txt_lines(tree):
            fd.write(line)


def convert_html_to_txt_lines(tree) -> Iterable[str]:
    rts = tree.findall(f'.//{NAMESPACE}rt')
    for rt in rts:
        rt.text = "(" + (rt.text or "")
        rt.tail = (rt.tail or "") + ")"

    ps = tree.findall(f'.//{NAMESPACE}p')
    for p in ps:
        yield ET.tostring(p, encoding="utf-8", method="text").decode("utf-8")


if __name__ == '__main__':
    typer.run(main)
