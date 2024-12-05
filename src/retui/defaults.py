from .enums import DimensionsFlag, Dock, TabIndex, TextAlign, WordWrap

_defaults = {
    "dock": Dock.NONE,
    "dimensions": DimensionsFlag.Absolute,
    "tab_index": TabIndex.TAB_INDEX_NOT_SELECTABLE,
    "tab_stop": False,
    "soft_border": False,
    "text_align": TextAlign.TopLeft,
    "text_wrap": WordWrap.Wrap,
    "scroll_horizontal": False,
    "scroll_vertical": False,
}


def default_value(key):
    return _defaults.get(key, None)
