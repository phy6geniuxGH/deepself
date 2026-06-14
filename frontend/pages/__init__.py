"""Register all nicegui pages. Importing this package wires every route.

main.py just needs `import frontend.pages` before ui.run_with(app).
"""

from nicegui import ui

from frontend.components.layout import page_header

# importing these modules executes their @ui.page decorators -> routes registered
from frontend.pages import idea, journal  # noqa: F401,E402


@ui.page("/")
def home_page() -> None:
    page_header("Home")
    with ui.column().classes("max-w-3xl mx-auto gap-4 p-4"):
        ui.label("deepself").classes("text-3xl font-bold")
        ui.label("Personal data ingestion + storage.").classes("text-gray-600")
        with ui.row().classes("gap-4"):
            ui.button("Journal", on_click=lambda: ui.navigate.to("/journal"))
            ui.button("Ideas", on_click=lambda: ui.navigate.to("/idea"))
