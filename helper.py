import json

from ascii_painter_engine import (
    Alignment,
    App,
    Color,
    ColorBits,
    ConsoleColor,
    ConsoleWidget,
    DimensionsFlag,
    mapping,
)

APP_DICT = {}


def register_app_dict(name, dict):
    global APP_DICT
    APP_DICT[name] = dict


def app_from_json(filename):
    with open(filename, "r") as f:
        app_json = json.load(f)

        # TODO: validate
        app = App()
        title = app_json["name"]
        if "title" in app_json:
            if len(app_json["title"]) > 0:
                title = app_json["title"]

        app.title = title
        app.color_mode(app_json.get("color", True))

        widget_id_dict = {}
        # widgets

        for widget_json in app_json["widgets"]:
            if widget_json.get("ignore", False):
                continue
            # mapping app dict values
            for key, value in widget_json.items():
                if type(value) is str and value.startswith("__"):
                    # this value needs mapping
                    path = value[2:]
                    steps = path.split("#")
                    curr_dict = APP_DICT
                    for step in steps[:-1]:
                        curr_dict = curr_dict.get(step, None)
                        if curr_dict is None:
                            raise Exception(f"No mapping for '{value}', recheck register_app_dict calls")
                    mapping_value = curr_dict.get(steps[-1], None)
                    if mapping_value is None:
                        raise Exception(f"No mapping for '{value}', recheck register_app_dict calls")
                    widget_json[key] = mapping_value

            # convert enums
            if type(widget_json["alignment"]) is str:
                widget_json["alignment"] = Alignment[widget_json["alignment"]]

            if type(widget_json["dimensions"]) is str:
                widget_json["dimensions"] = DimensionsFlag[widget_json["dimensions"]]

            widget_type = widget_json.get("type", None)
            if type(widget_type) is str:
                widget_class = mapping.get_widget_class(widget_type)
                if widget_class is None:
                    widget_class = mapping.import_widget_class(widget_type)
                    if widget_class is None:
                        raise Exception(f"Unknown widget type: '{widget_type}'")
            elif issubclass(type(widget_type), ConsoleWidget):
                widget_class = widget_type
            else:
                raise Exception(f"widget[{widget_json['id']}] is of type: {type(widget_type)}")

            widget_json["app"] = app

            if "border_color" in widget_json:
                fg_color = Color(
                    widget_json["border_color"]["fg"]["val"], ColorBits[widget_json["border_color"]["fg"]["color_bits"]]
                )
                bg_color = Color(
                    widget_json["border_color"]["bg"]["val"], ColorBits[widget_json["border_color"]["bg"]["color_bits"]]
                )
                widget_json["border_color"] = ConsoleColor(fg_color, bg_color)

            widget = widget_class.from_dict(**widget_json)

            widget_id = widget_json.get("id", None)
            if widget_id:
                widget_id_dict[widget_id] = widget
            # if has id - add it to dict
            parent = app
            parent_id = widget_json.get("parent_id", None)
            if parent_id:
                parent = widget_id_dict.get(parent_id, None)
                if parent is None:
                    raise Exception(f"Given parent_id: '{parent_id}' doesnt match already defined id of widget")
            parent.add_widget(widget)
        return app
