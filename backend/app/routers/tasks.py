"""Task planner: CRUD + AI study-plan generation."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security
from ..services import llm, vectorstore

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    return (db.query(models.Task)
            .filter(models.Task.user_id == user.id)
            .order_by(models.Task.due_date.asc().nullslast(),
                      models.Task.created_at.desc())
            .all())


@router.post("", response_model=schemas.TaskOut, status_code=201)
def create_task(
    body: schemas.TaskCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    task = models.Task(user_id=user.id, **body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: str,
    body: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    task = (db.query(models.Task)
            .filter(models.Task.id == task_id, models.Task.user_id == user.id)
            .first())
    if not task:
        raise HTTPException(404, "Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    task = (db.query(models.Task)
            .filter(models.Task.id == task_id, models.Task.user_id == user.id)
            .first())
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()
    return None


@router.post("/study-plan", response_model=list[schemas.TaskOut], status_code=201)
def generate_study_plan(
    body: schemas.StudyPlanRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    # Pull related material from the knowledge base for context
    context = ""
    try:
        hits = vectorstore.search(user.id, body.goal, limit=4)
        context = "\n\n".join(h["text"] for h in hits)
    except Exception:
        pass

    plan = llm.generate_study_plan(body.goal, body.days, body.hours_per_day, context)

    created = []
    start = datetime.utcnow()
    for item in plan:
        task = models.Task(
            user_id=user.id,
            title=item["title"],
            description=item["description"],
            priority=item["priority"] if item["priority"] in ("low", "medium", "high") else "medium",
            due_date=(start + timedelta(days=item["day"] - 1)).date().isoformat(),
            source="ai_plan",
        )
        db.add(task)
        created.append(task)
    db.commit()
    for t in created:
        db.refresh(t)
    return created
