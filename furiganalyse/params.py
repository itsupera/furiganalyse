from enum import Enum


class FuriganaMode(str, Enum):
    add = "add"
    replace = "replace"
    remove = "remove"


class OutputFormat(str, Enum):
    epub = "epub"
    many_txt = "many_txt"
    single_txt = "single_txt"
    apkg = "apkg"
    html = "html"


class WritingMode(str, Enum):
    horizontal_tb = "horizontal-tb"
    vertical_rl = "vertical-rl"
    vertical_lr = "vertical-lr"