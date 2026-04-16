from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from infrastructure.supabase_repo import supabase

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(user: UserCreate):
    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        if response.user:
            return {"message": "User registered successfully", "user": response.user}
        raise HTTPException(status_code=400, detail="Registration failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
        })
        if response.session:
            return {
                "access_token": response.session.access_token,
                "token_type": "bearer"
            }
        raise HTTPException(status_code=400, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

import os

@router.get("/login/google")
def login_google():
    try:
        supabase_url = os.getenv("SUPABASE_URL", "https://hqxjqbuppbfqenlkryql.supabase.co")
        url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to=http://localhost:3000"
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

