from .enums import Alignment, DimensionsFlag, TabIndex, TextAlign, WordWrap

_defaults = {
    "alignment": Alignment.TopLeft,
    "dimensions": DimensionsFlag.Absolute,
    "tab_index": TabIndex.TAB_INDEX_NOT_SELECTABLE,
    "soft_border": False,
    "text_align": TextAlign.TopLeft,
    "text_wrap": WordWrap.Wrap,
    "scroll_horizontal": False,
    "scroll_vertical": False,
}


def default_value(key):
    return _defaults.get(key, None)
