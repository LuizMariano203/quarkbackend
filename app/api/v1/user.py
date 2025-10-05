# app/api/v1/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.get(
    "/profile", 
    response_model=schemas.UserOut,
    summary="Obter Perfil do Usuário",
    description="Retorna os dados básicos do usuário autenticado (ID, email, status KYC)."
)
def get_user_profile(
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Recupera os dados completos do perfil do usuário autenticado.
    """
    return current_user

# NOVO ENDPOINT ADICIONADO ABAIXO
@router.post(
    "/kyc/start",
    response_model=schemas.UserOut,
    summary="Iniciar Processo KYC",
    description="Altera o status do KYC do usuário para 'PENDING' e simula o início da verificação de identidade. Usuários com status 'VERIFIED' ou 'FAILED' não podem iniciar um novo processo."
)
def start_kyc_process(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    # 1. Prevenção: Se o usuário já estiver VERIFICADO, não permite iniciar um novo processo.
    if current_user.kyc_status == models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="KYC is already verified for this user.")

    # 2. Início do Bloco Transacional
    try:
        # Se o status atual for 'PENDING', não faz nada e retorna o status atual.
        if current_user.kyc_status != models.KYCStatus.PENDING:
            current_user.kyc_status = models.KYCStatus.PENDING
            db.commit()
            db.refresh(current_user)
        
        # Simulação de integração externa:
        # Aqui, em um ambiente real, você faria uma chamada para o serviço de KYC/KYB
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao iniciar KYC: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while starting KYC process.")

    return current_user