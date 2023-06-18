import json

from ascii_painter_engine import App, Color, ColorBits, ConsoleColor, mapping


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
            widget_type = widget_json.get("type", None)
            widget_class = mapping.GetWidgetClass(widget_type)
            if widget_class is None:
                raise Exception(f"Unknown widget type: '{widget_type}'")
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
