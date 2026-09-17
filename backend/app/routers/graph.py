"""Knowledge graph: nodes (documents) + edges (semantic links)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=schemas.GraphResponse)
def get_graph(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    docs = (db.query(models.Document)
            .filter(models.Document.user_id == user.id,
                    models.Document.status == "ready")
            .all())
    doc_ids = {d.id for d in docs}

    links = (db.query(models.DocumentLink)
             .filter(models.DocumentLink.user_id == user.id)
             .all())

    # De-duplicate bidirectional edges
    seen, edges = set(), []
    for link in links:
        if link.source_id not in doc_ids or link.target_id not in doc_ids:
            continue
        key = tuple(sorted([link.source_id, link.target_id]))
        if key in seen:
            continue
        seen.add(key)
        edges.append(schemas.GraphEdge(source=link.source_id, target=link.target_id,
                                       similarity=link.similarity))

    nodes = [schemas.GraphNode(
        id=d.id, label=d.title, file_type=d.file_type,
        tags=d.tags or [], summary=(d.summary or "")[:200],
    ) for d in docs]

    return schemas.GraphResponse(nodes=nodes, edges=edges)
