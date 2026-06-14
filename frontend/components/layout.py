"""Shared page chrome. Call page_header() at the top of each page builder."""

from nicegui import ui

NAV = [("Home", "/"), ("Journal", "/journal"), ("Ideas", "/idea")]


def page_header(active: str) -> None:
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("deepself").classes("text-xl font-bold")
        with ui.row().classes("gap-4"):
            for title, path in NAV:
                link = ui.link(title, path).classes("text-white no-underline")
                if title == active:
                    link.classes("font-bold underline")
