import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Intervention, Student, AuditLog
from backend.schemas import InterventionCreate, InterventionUpdate, InterventionStatusUpdate, InterventionOut
from backend.auth import get_current_user

router = APIRouter(prefix="/interventions", tags=["Intervention Center"])

@router.get("", response_model=List[InterventionOut])
def list_interventions(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    category_filter: Optional[str] = Query(None, alias="category"),
    student_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Intervention).join(Student, Intervention.student_id == Student.id)

    if status_filter and status_filter != "All":
        query = query.filter(Intervention.status == status_filter)
    if priority_filter and priority_filter != "All":
        query = query.filter(Intervention.priority == priority_filter)
    if category_filter and category_filter != "All":
        query = query.filter(Intervention.category == category_filter)
    if student_id:
        query = query.filter(Intervention.student_id == student_id)

    interventions = query.order_by(Intervention.created_at.desc()).all()
    
    out = []
    for i in interventions:
        item = InterventionOut.model_validate(i)
        item.student_name = i.student.name if i.student else i.student_id
        item.student_dept = i.student.department if i.student else ""
        out.append(item)
    return out

@router.post("", response_model=InterventionOut, status_code=status.HTTP_201_CREATED)
def create_intervention(
    data: InterventionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {data.student_id} not found")

    intervention = Intervention(
        student_id=data.student_id,
        title=data.title,
        category=data.category,
        issue=data.issue,
        action_plan=data.action_plan,
        assigned_to_user_id=current_user.id,
        assigned_to_name=data.assigned_to_name or current_user.full_name,
        priority=data.priority,
        status="Open",
        due_date=data.due_date,
        follow_up_date=data.follow_up_date,
        notes=data.notes or ""
    )
    db.add(intervention)
    db.flush()

    # Log audit
    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="CREATE_INTERVENTION",
        target_type="INTERVENTION",
        target_id=str(intervention.id),
        details=f"Created {intervention.priority} priority intervention for {student.name} ({student.id}): {intervention.title}"
    )
    db.add(log)
    db.commit()
    db.refresh(intervention)

    item = InterventionOut.model_validate(intervention)
    item.student_name = student.name
    item.student_dept = student.department
    return item

@router.patch("/{intervention_id}/status", response_model=InterventionOut)
def update_intervention_status(
    intervention_id: int,
    status_update: InterventionStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    old_status = intervention.status
    intervention.status = status_update.status
    if status_update.notes:
        intervention.notes = (intervention.notes + "\n" if intervention.notes else "") + f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d')}]: {status_update.notes}"

    if status_update.status == "Completed":
        intervention.completed_at = datetime.datetime.utcnow()
    elif old_status == "Completed" and status_update.status != "Completed":
        intervention.completed_at = None

    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="UPDATE_INTERVENTION_STATUS",
        target_type="INTERVENTION",
        target_id=str(intervention.id),
        details=f"Status changed from '{old_status}' to '{status_update.status}'"
    )
    db.add(log)
    db.commit()
    db.refresh(intervention)

    item = InterventionOut.model_validate(intervention)
    item.student_name = intervention.student.name if intervention.student else intervention.student_id
    item.student_dept = intervention.student.department if intervention.student else ""
    return item

@router.put("/{intervention_id}", response_model=InterventionOut)
def update_intervention(
    intervention_id: int,
    data: InterventionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if data.title is not None: intervention.title = data.title
    if data.category is not None: intervention.category = data.category
    if data.issue is not None: intervention.issue = data.issue
    if data.action_plan is not None: intervention.action_plan = data.action_plan
    if data.priority is not None: intervention.priority = data.priority
    if data.assigned_to_name is not None: intervention.assigned_to_name = data.assigned_to_name
    if data.due_date is not None: intervention.due_date = data.due_date
    if data.follow_up_date is not None: intervention.follow_up_date = data.follow_up_date
    if data.notes is not None: intervention.notes = data.notes
    if data.status is not None:
        intervention.status = data.status
        if data.status == "Completed" and not intervention.completed_at:
            intervention.completed_at = datetime.datetime.utcnow()

    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="UPDATE_INTERVENTION",
        target_type="INTERVENTION",
        target_id=str(intervention.id),
        details=f"Updated details of intervention #{intervention.id}"
    )
    db.add(log)
    db.commit()
    db.refresh(intervention)

    item = InterventionOut.model_validate(intervention)
    item.student_name = intervention.student.name if intervention.student else intervention.student_id
    item.student_dept = intervention.student.department if intervention.student else ""
    return item

@router.delete("/{intervention_id}")
def delete_intervention(
    intervention_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="DELETE_INTERVENTION",
        target_type="INTERVENTION",
        target_id=str(intervention.id),
        details=f"Deleted intervention '{intervention.title}'"
    )
    db.add(log)
    db.delete(intervention)
    db.commit()
    return {"message": "Intervention deleted successfully"}

