"""Theme choices shared by ODIA's Textual screens."""

DEFAULT_UI_THEME = "flexoki"

UI_THEME_OPTIONS = (
    ("Flexoki", "flexoki"),
    ("Gruvbox", "gruvbox"),
    ("Rosé Pine", "rose-pine"),
    ("Tokyo Night", "tokyo-night"),
    ("Monokai", "monokai"),
    ("Textual Dark", "textual-dark"),
    ("Textual Light", "textual-light"),
)

UI_THEME_NAMES = tuple(theme_name for _, theme_name in UI_THEME_OPTIONS)
