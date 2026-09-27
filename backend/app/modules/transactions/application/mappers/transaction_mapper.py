from ...domain.entities import TransactionRecord
from ..dto.response.transaction_responses import TransactionResponse


def to_transaction_response(transaction: TransactionRecord) -> TransactionResponse:
    return TransactionResponse.model_validate(transaction)
