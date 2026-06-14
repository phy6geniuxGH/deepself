"""Journal page. Importing this module registers the /journal route."""

from nicegui import ui

from frontend import services
from frontend.components.layout import page_header


@ui.page("/journal")
def journal_page() -> None:
    # everything inside runs per page-visit, building a fresh UI tree for that client
    page_header("Journal")

    with ui.column().classes("w-full max-w-3xl mx-auto gap-4 p-4"):
        ui.label("Daily Journal").classes("text-2xl font-bold")

        # --- add form ---
        with ui.card().classes("w-full"):
            body = ui.textarea("What happened today?").props("outlined autogrow").classes("w-full")
            with ui.row().classes("w-full gap-2"):
                mood = ui.input("Mood").classes("flex-1")
                tags = ui.input("Tags (comma-separated)").classes("flex-1")

            def add() -> None:
                if not body.value.strip():
                    ui.notify("Entry is empty", type="warning")
                    return
                services.create_journal(body.value, mood.value, tags.value)
                body.value = mood.value = tags.value = ""
                feed.refresh()                      # re-run the @ui.refreshable below
                ui.notify("Saved", type="positive")

            ui.button("Add entry", on_click=add).props("color=primary")

        # --- csv/xlsx upload ---
        with ui.card().classes("w-full"):
            ui.label("Bulk import (.csv / .xlsx)").classes("font-semibold")

            def on_upload(e) -> None:
                res = services.import_journal(e.content.read(), e.name)
                feed.refresh()
                msg = f"Imported {res['imported']}"
                if res["errors"]:
                    msg += f", {len(res['errors'])} row error(s)"
                ui.notify(msg, type="positive" if not res["errors"] else "warning")

            ui.upload(on_upload=on_upload, auto_upload=True).props("accept=.csv,.xlsx").classes("w-full")

        # --- search ---
        with ui.card().classes("w-full"):
            search_box = ui.input("Semantic search").props("clearable").classes("w-full")

            @ui.refreshable
            def results() -> None:
                q = (search_box.value or "").strip()
                if not q:
                    return
                for jr, dist in services.search_journals(q, k=10):
                    with ui.card().classes("w-full"):
                        ui.markdown(jr.body_md)
                        ui.label(f"score {1 - dist:.2f} · {', '.join(jr.tags)}").classes("text-xs text-gray-500")

            search_box.on("keydown.enter", lambda: results.refresh())
            results()

        # --- feed ---
        ui.label("Recent").classes("text-lg font-semibold")

        @ui.refreshable
        def feed() -> None:
            entries = services.list_journals()
            if not entries:
                ui.label("No entries yet.").classes("text-gray-500")
                return
            for jr in entries:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full justify-between items-start"):
                        ui.markdown(jr.body_md).classes("flex-1")
                        ui.button(icon="delete", on_click=lambda _, i=jr.id: _remove(i)).props("flat dense round")
                    meta = jr.occurred_at.strftime("%Y-%m-%d %H:%M")
                    if jr.mood:
                        meta += f" · mood: {jr.mood}"
                    if jr.tags:
                        meta += f" · {', '.join(jr.tags)}"
                    ui.label(meta).classes("text-xs text-gray-500")

        def _remove(entry_id: int) -> None:
            services.delete_journal(entry_id)
            feed.refresh()
            ui.notify("Deleted", type="info")

        feed()
