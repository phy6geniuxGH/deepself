from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import projections
from backend.db.engine import get_session
from backend.db.models import Entry, EntryType, IdeaDetail, IdeaStatus
from backend.ingestion import manual
from backend.ingestion.files import import_file
from backend.projections import vectors
from backend.schemas.common import SearchHit
from backend.schemas.idea import IdeaCreate, IdeaRead

router = APIRouter(prefix="/idea", tags=["idea"])
ASPECT = "idea"


def _to_read(e: Entry) -> IdeaRead:
    return IdeaRead.from_entry(e)


def _get_or_404(s: Session, entry_id: int) -> Entry:
    e = s.get(Entry, entry_id)
    if e is None or e.type != EntryType.idea:
        raise HTTPException(404, "idea not found")
    return e


@router.post("", response_model=IdeaRead, status_code=201)
def create(data: IdeaCreate, s: Session = Depends(get_session)):
    e = manual.create_idea(s, data)
    projections.project_entry(s, e)
    return _to_read(e)


@router.get("", response_model=list[IdeaRead])
def list_ideas(
    status: IdeaStatus | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    s: Session = Depends(get_session),
):
    stmt = select(Entry).where(Entry.type == EntryType.idea)
    if status is not None:
        stmt = stmt.join(IdeaDetail).where(IdeaDetail.status == status)
    stmt = stmt.order_by(Entry.occurred_at.desc()).limit(limit).offset(offset)
    return [_to_read(e) for e in s.scalars(stmt).all()]


@router.get("/search", response_model=list[SearchHit[IdeaRead]])
def search(q: str, k: int = Query(10, le=50), s: Session = Depends(get_session)):
    hits = vectors.search(s, q, k=k, entry_type=EntryType.idea.value)
    if not hits:
        return []
    found = {e.id: e for e in s.scalars(select(Entry).where(Entry.id.in_([h[0] for h in hits]))).all()}
    return [
        SearchHit(distance=dist, entry=_to_read(found[i]))
        for i, dist in hits
        if i in found
    ]


@router.get("/{entry_id}", response_model=IdeaRead)
def get_one(entry_id: int, s: Session = Depends(get_session)):
    return _to_read(_get_or_404(s, entry_id))


@router.patch("/{entry_id}/status", response_model=IdeaRead)
def set_status(entry_id: int, status: IdeaStatus, s: Session = Depends(get_session)):
    e = _get_or_404(s, entry_id)
    e.idea_detail.status = status
    s.flush()
    return _to_read(e)


@router.delete("/{entry_id}", status_code=204)
def delete(entry_id: int, s: Session = Depends(get_session)):
    e = _get_or_404(s, entry_id)
    projections.remove_entry(s, e)
    s.delete(e)


@router.post("/upload")
async def upload(file: UploadFile = File(...), s: Session = Depends(get_session)):
    content = await file.read()
    try:
        result = import_file(s, ASPECT, content, file.filename)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    for e in result.entries:
        projections.project_entry(s, e)
    return {"imported": result.ok, "errors": result.errors}
