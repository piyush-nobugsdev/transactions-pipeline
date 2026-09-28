from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from ..application.dto.request.transaction_requests import CreateTransactionRequest
from ..application.dto.response.transaction_responses import TransactionListResponse, TransactionResponse
from ..application.mappers.transaction_mapper import to_transaction_response
from ..application.services.transaction_service import TransactionService
from .dependencies import get_transaction_service

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    request: CreateTransactionRequest,
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    return to_transaction_response(await service.create_transaction(request))


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    job_id: UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionListResponse:
    transactions = await service.list_transactions(job_id=job_id, offset=offset, limit=limit)
    return TransactionListResponse(
        items=[to_transaction_response(item) for item in transactions],
        offset=offset,
        limit=limit,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    return to_transaction_response(await service.get_transaction(transaction_id))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    service: TransactionService = Depends(get_transaction_service),
) -> Response:
    await service.delete_transaction(transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
