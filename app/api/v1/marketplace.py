# app/api/v1/marketplace.py (ADICIONADO ENDPOINT /matches/{search_id})

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Union # Adicionado Union
from ... import models, schemas
from ...core import database, security
from sqlalchemy import or_ # Importado 'or_' para filtros complexos

router = APIRouter()

@router.post(
    "/offers", 
    response_model=schemas.CreditOfferOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Criar Nova Oferta de Crédito",
    description="Permite que um usuário verificado (Credor) crie e publique uma nova oferta de crédito no marketplace."
)
def create_credit_offer(
    offer_in: schemas.CreditOfferCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.kyc_status != models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="User must be KYC verified to create offers")
    
    try:
        new_offer = models.CreditOffer(**offer_in.dict(), lender_id=current_user.id)
        db.add(new_offer)
        db.commit()
        db.refresh(new_offer)
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar oferta: {e}")
        raise HTTPException(status_code=500, detail="Could not create credit offer.")
        
    return new_offer

@router.get(
    "/offers", 
    response_model=List[schemas.CreditOfferOut],
    summary="Listar Ofertas Elegíveis",
    description="Retorna todas as ofertas de crédito ATIVAS no marketplace para as quais o usuário não é o Credor. (Filtros de score e setor não implementados nesta versão)."
)
def get_eligible_offers(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    offers = db.query(models.CreditOffer).filter(
        models.CreditOffer.status == models.OfferStatus.ACTIVE,
        models.CreditOffer.lender_id != current_user.id
    ).all()
    return offers

@router.post(
    "/searches",
    response_model=schemas.CreditSearchOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Busca de Crédito",
    description="Permite que um Mutuário crie uma busca ativa por crédito, definindo o valor desejado, taxa máxima de juros e prazo."
)
def create_credit_search(
    search_in: schemas.CreditSearchCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Regra de Negócio: Mutuário deve ser verificado para pedir crédito
    if current_user.kyc_status != models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="User must be KYC verified to create a search for credit.")

    try:
        new_search = models.CreditSearch(**search_in.dict(), borrower_id=current_user.id)
        db.add(new_search)
        db.commit()
        db.refresh(new_search)
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar busca de crédito: {e}")
        raise HTTPException(status_code=500, detail="Could not create credit search.")
        
    return new_search

# NOVO ENDPOINT ADICIONADO ABAIXO: Listar Ofertas Compatíveis com a Busca
@router.get(
    "/matches/{search_id}",
    response_model=List[schemas.CreditOfferOut],
    summary="Consultar Ofertas Compatíveis com Busca",
    description="Permite que um Mutuário (ou um Credor, opcionalmente) visualize quais ofertas ATIVAS de crédito disponíveis no mercado se encaixam nos critérios de uma Busca de Crédito (search_id) específica."
)
def get_matching_offers(
    search_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    # 1. Recupera a busca do usuário (apenas se ele for o criador ou se for um Admin)
    credit_search = db.query(models.CreditSearch).filter(
        models.CreditSearch.id == search_id,
        or_(models.CreditSearch.borrower_id == current_user.id, current_user.id == 1) # Permite que o criador ou admin consulte
    ).first()

    if not credit_search:
        raise HTTPException(status_code=404, detail="Credit search not found or unauthorized.")
    
    # 2. Busca ofertas que dão MATCH nos critérios da busca
    # Critérios de Match (baseados na lógica inversa da oferta):
    # a) Oferta deve estar ATIVA
    # b) Valor Máximo da Oferta >= Valor Desejado na Busca
    # c) Juros da Oferta <= Juros Máximo Aceito na Busca
    # d) Prazo da Oferta <= Prazo Desejado na Busca (o mutuário prefere pagar mais rápido)
    # e) Score Mínimo Exigido na Oferta <= Score do Usuário (Assumindo que o score do usuário está no objeto current_user, embora o campo não esteja no schema.UserOut, vamos recuperá-lo do modelo User completo.)
    
    # Buscamos o score do usuário (borrower)
    borrower_score = db.query(models.User.score_credito).filter(models.User.id == credit_search.borrower_id).scalar()
    if borrower_score is None:
         # Este caso não deveria ocorrer se o registro de usuário estiver completo
         raise HTTPException(status_code=400, detail="Borrower credit score not available.")


    offers = db.query(models.CreditOffer).filter(
        models.CreditOffer.status == models.OfferStatus.ACTIVE,
        models.CreditOffer.lender_id != current_user.id, # Credor não pode ver suas próprias ofertas
        models.CreditOffer.max_amount >= credit_search.desired_amount,
        models.CreditOffer.interest_rate <= credit_search.max_interest_rate,
        models.CreditOffer.term_months <= credit_search.desired_term_months,
        models.CreditOffer.min_credit_score <= borrower_score
    ).all()
    
    return offers