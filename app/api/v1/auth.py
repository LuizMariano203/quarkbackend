# app/api/v1/auth.py (CORRIGIDO: Passando todos os campos do schema para models.User)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ... import models, schemas
from ...core import security, database

router = APIRouter()

@router.post(
    "/register", 
    response_model=schemas.UserOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Registro de Usuário",
    description="Realiza o cadastro inicial de um novo Mutuário ou Credor, cria sua carteira (Account) e gera o hash da senha."
)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # 1. Checagem de e-mail
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(user_in.password)
    
    try:
        # 2. Criação do Usuário com TODOS os novos campos do schema
        # Usamos .dict(exclude={'password'}) para pegar todos os campos exceto a senha
        user_data = user_in.dict(exclude={'password'})
        
        new_user = models.User(
            **user_data,
            hashed_password=hashed_password
        )
        db.add(new_user)
        db.flush() 
        
        # 3. Criação da Carteira (Account)
        new_account = models.Account(owner_id=new_user.id)
        db.add(new_account)
        
        db.commit() 
    except Exception as e:
        db.rollback()
        # Imprime o erro detalhado para ajudar no debugging se for outro problema
        print(f"Erro ao criar usuário: {e}") 
        raise HTTPException(status_code=500, detail="Failed to create user account.")

    db.refresh(new_user)
    return new_user

@router.post(
    "/login", 
    response_model=schemas.Token,
    summary="Login e Geração de Token",
    description="Autentica o usuário usando email e senha (OAuth2) e retorna um token JWT de acesso."
)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password", 
        )
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}