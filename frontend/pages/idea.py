"""Idea Dumps page. Importing this module registers the /idea route."""

from nicegui import ui

from backend.db.models import IdeaStatus
from frontend import services
from frontend.components.layout import page_header

_STATUSES = [s.value for s in IdeaStatus]


@ui.page("/idea")
def idea_page() -> None:
    page_header("Ideas")

    with ui.column().classes("w-full max-w-3xl mx-auto gap-4 p-4"):
        ui.label("Idea Dumps").classes("text-2xl font-bold")

        # --- quick capture ---
        with ui.card().classes("w-full"):
            body = ui.textarea("Dump an idea...").props("outlined autogrow").classes("w-full")
            tags = ui.input("Tags (comma-separated)").classes("w-full")

            def add() -> None:
                if not body.value.strip():
                    ui.notify("Idea is empty", type="warning")
                    return
                services.create_idea(body.value, tags.value)
                body.value = tags.value = ""
                feed.refresh()
                ui.notify("Captured", type="positive")

            ui.button("Capture", on_click=add).props("color=primary")

        # --- upload ---
        with ui.card().classes("w-full"):
            ui.label("Bulk import (.csv / .xlsx)").classes("font-semibold")

            def on_upload(e) -> None:
                res = services.import_idea(e.content.read(), e.name)
                feed.refresh()
                ui.notify(f"Imported {res['imported']}", type="positive")

            ui.upload(on_upload=on_upload, auto_upload=True).props("accept=.csv,.xlsx").classes("w-full")

        # --- review queue with status filter ---
        with ui.row().classes("items-center gap-2"):
            ui.label("Review queue").classes("text-lg font-semibold")
            status_filter = ui.select(
                ["all", *_STATUSES], value="all", on_change=lambda: feed.refresh()
            ).props("dense")

        @ui.refreshable
        def feed() -> None:
            sel = status_filter.value
            status = None if sel == "all" else IdeaStatus(sel)
            ideas = services.list_ideas(status=status)
            if not ideas:
                ui.label("Nothing here.").classes("text-gray-500")
                return
            for ir in ideas:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full justify-between items-start"):
                        ui.markdown(ir.body_md).classes("flex-1")
                        ui.button(icon="delete", on_click=lambda _, i=ir.id: _remove(i)).props("flat dense round")
                    with ui.row().classes("items-center gap-2"):
                        ui.select(
                            _STATUSES, value=ir.status.value,
                            on_change=lambda e, i=ir.id: _set_status(i, e.value),
                        ).props("dense")
                        if ir.tags:
                            ui.label(", ".join(ir.tags)).classes("text-xs text-gray-500")

        def _set_status(entry_id: int, value: str) -> None:
            services.set_idea_status(entry_id, IdeaStatus(value))
            feed.refresh()
            ui.notify(f"-> {value}", type="info")

        def _remove(entry_id: int) -> None:
            services.delete_idea(entry_id)
            feed.refresh()
            ui.notify("Deleted", type="info")

        feed()
