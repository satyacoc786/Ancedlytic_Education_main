import datetime
import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Student, User, WebAuthnChallenge, WebAuthnCredential
from backend.schemas import LoginRequest, StudentRegistrationRequest, TeacherRegistrationRequest, TokenResponse, UserOut
from backend.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.config import settings
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json, base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class FaceEnrollmentRequest(BaseModel):
    username_or_id: str
    password: str


class FaceLoginOptionsRequest(BaseModel):
    username_or_id: str


class FaceCredentialResponse(BaseModel):
    challenge: str
    credential: Dict[str, Any]


def _save_challenge(db: Session, challenge: bytes, user_id: int | None, purpose: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.expires_at < now
    ).delete()
    challenge_text = bytes_to_base64url(challenge)
    db.add(WebAuthnChallenge(
        challenge=challenge_text,
        user_id=user_id,
        purpose=purpose,
        rp_id=settings.WEB_AUTHN_RP_ID,
        origin=settings.WEB_AUTHN_ORIGIN,
        expires_at=now + datetime.timedelta(minutes=3),
    ))
    db.commit()
    return challenge_text


def _consume_challenge(db: Session, challenge: str, purpose: str) -> WebAuthnChallenge:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    saved = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.challenge == challenge,
        WebAuthnChallenge.purpose == purpose,
        WebAuthnChallenge.expires_at >= now,
    ).first()
    if not saved:
        raise HTTPException(status_code=400, detail="Authentication request expired. Try again.")
    db.delete(saved)
    db.commit()
    return saved


def _token_for_user(user: User) -> Dict[str, Any]:
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "name": user.full_name,
        "id": user.id,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.full_name,
            "role": user.role,
        },
    }

@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    # 1. Check if it's a staff User
    user = db.query(User).filter(
        (User.username == creds.username_or_id) | (User.email == creds.username_or_id)
    ).first()

    if user:
        if not user.is_active or not verify_password(creds.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        return _token_for_user(user)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials. User not found."
    )


@router.post("/register-student", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_student(payload: StudentRegistrationRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == payload.student_id, User.email == payload.email)
    ).first()
    existing_student = db.query(Student).filter(
        or_(Student.id == payload.student_id, Student.email == payload.email)
    ).first()
    if existing or existing_student:
        raise HTTPException(status_code=409, detail="That student ID or email is already registered.")

    today = datetime.date.today()
    user = User(
        username=payload.student_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="student",
    )
    student = Student(
        id=payload.student_id,
        name=payload.full_name,
        email=payload.email,
        department=payload.department,
        semester=1,
        academic_year=f"{today.year}-{today.year + 1}",
        avatar=payload.full_name[0].upper(),
    )
    db.add_all([user, student])
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That student ID or email is already registered.")
    return _token_for_user(user)


@router.post("/register-teacher", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_teacher(payload: TeacherRegistrationRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == payload.teacher_id, User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="That teacher ID or email is already registered.")

    user = User(
        username=payload.teacher_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="faculty",
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That teacher ID or email is already registered.")
    return _token_for_user(user)


@router.post("/face/register/options")
def face_registration_options(payload: FaceEnrollmentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username_or_id).first()
    if not user or user.role != "student" or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Enter a valid student ID and password to set up Face ID.")

    existing = db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user.id).all()
    options = generate_registration_options(
        rp_id=settings.WEB_AUTHN_RP_ID,
        rp_name=settings.WEB_AUTHN_RP_NAME,
        user_id=user.username.encode("utf-8"),
        user_name=user.username,
        user_display_name=user.full_name,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            require_resident_key=True,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id))
            for item in existing
        ],
    )
    _save_challenge(db, options.challenge, user.id, "registration")
    return json.loads(options_to_json(options))


@router.post("/face/register/verify")
def verify_face_registration(payload: FaceCredentialResponse, db: Session = Depends(get_db)):
    challenge = _consume_challenge(db, payload.challenge, "registration")
    try:
        verified = verify_registration_response(
            credential=payload.credential,
            expected_challenge=base64url_to_bytes(challenge.challenge),
            expected_rp_id=challenge.rp_id,
            expected_origin=challenge.origin,
            require_user_verification=True,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Face ID setup could not be verified. Try again.")

    credential_id = bytes_to_base64url(verified.credential_id)
    credential = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.credential_id == credential_id
    ).first()
    if credential and credential.user_id != challenge.user_id:
        raise HTTPException(status_code=409, detail="This device credential is already registered to another account.")
    if not credential:
        credential = WebAuthnCredential(
            user_id=challenge.user_id,
            credential_id=credential_id,
            public_key=bytes_to_base64url(verified.credential_public_key),
            sign_count=verified.sign_count,
        )
        db.add(credential)
    else:
        credential.public_key = bytes_to_base64url(verified.credential_public_key)
        credential.sign_count = verified.sign_count
    db.commit()
    return {"message": "Face ID is ready on this device."}


@router.post("/face/login/options")
def face_login_options(payload: FaceLoginOptionsRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == payload.username_or_id,
        User.role == "student",
        User.is_active.is_(True),
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student account not found.")
    credentials = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.user_id == user.id
    ).all()
    if not credentials:
        raise HTTPException(status_code=404, detail="Set up Face ID for this student first.")
    options = generate_authentication_options(
        rp_id=settings.WEB_AUTHN_RP_ID,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id))
            for item in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    _save_challenge(db, options.challenge, user.id, "authentication")
    return json.loads(options_to_json(options))


@router.post("/face/login/verify", response_model=TokenResponse)
def verify_face_login(payload: FaceCredentialResponse, db: Session = Depends(get_db)):
    challenge = _consume_challenge(db, payload.challenge, "authentication")
    try:
        credential_id = bytes_to_base64url(base64url_to_bytes(payload.credential["rawId"]))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid passkey response.")

    saved_credential = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.credential_id == credential_id
    ).first()
    if not saved_credential or saved_credential.user_id != challenge.user_id:
        raise HTTPException(status_code=401, detail="No matching Face ID credential was found.")
    user = db.query(User).filter(User.id == saved_credential.user_id).first()
    if not user or user.role != "student" or not user.is_active:
        raise HTTPException(status_code=401, detail="Student account is unavailable.")

    try:
        verified = verify_authentication_response(
            credential=payload.credential,
            expected_challenge=base64url_to_bytes(challenge.challenge),
            expected_rp_id=challenge.rp_id,
            expected_origin=challenge.origin,
            credential_public_key=base64url_to_bytes(saved_credential.public_key),
            credential_current_sign_count=saved_credential.sign_count,
            require_user_verification=True,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Face ID verification failed.")

    saved_credential.sign_count = verified.new_sign_count
    db.commit()
    return _token_for_user(user)

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.full_name,
        "role": current_user.role
    }

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}

