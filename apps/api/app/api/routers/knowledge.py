from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.knowledge_deposit_decisions import (
    approve_knowledge_deposit_result,
    reject_knowledge_deposit_result,
)
from app.services.knowledge_deposits import (
    create_knowledge_document_result,
    delete_knowledge_document_result,
    knowledge_deposit_list_response,
    knowledge_write_store,
    patch_knowledge_document_result,
    retry_knowledge_document_index_result,
)
from app.services.knowledge_documents import knowledge_document_list_response
from app.services.knowledge_search import knowledge_search_response

router = APIRouter(tags=["knowledge"])


class KnowledgeDocumentRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "manual"
    product_id: str | None = None
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])
    tags: list[str] = Field(default_factory=list)


class KnowledgeDocumentPatchRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    doc_type: str | None = None
    product_id: str | None = None
    permission_roles: list[str] | None = None
    tags: list[str] | None = None
    index_status: str | None = None
    index_error: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 8


class KnowledgeDepositApproveRequest(BaseModel):
    title: str | None = None
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])


class KnowledgeDepositRejectRequest(BaseModel):
    reason: str


@router.get("/api/knowledge/documents")
def list_knowledge_documents(
    request: Request,
    keyword: str | None = None,
    doc_type: str | None = None,
    index_status: str | None = None,
    permission_role: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return knowledge_document_list_response(
        current_store=store(request),
        doc_type=doc_type,
        index_status=index_status,
        keyword=keyword,
        page=page,
        page_size=page_size,
        permission_role=permission_role,
        request=request,
        sort_by=sort_by,
        sort_order=sort_order,
        user=user,
    )


@router.post("/api/knowledge/documents")
def create_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    document = create_knowledge_document_result(
        content=payload.content,
        current_store=knowledge_write_store(store(request)),
        doc_type=payload.doc_type,
        permission_roles=payload.permission_roles,
        product_id=payload.product_id,
        tags=payload.tags,
        title=payload.title,
        user=user,
    )
    return envelope(
        document,
        get_trace_id(request),
    )


@router.patch("/api/knowledge/documents/{document_id}")
def patch_knowledge_document(
    document_id: str,
    request: Request,
    payload: KnowledgeDocumentPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    document = patch_knowledge_document_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        payload=payload,
        user=user,
    )
    return envelope(
        document,
        get_trace_id(request),
    )


@router.post("/api/knowledge/documents/{document_id}/retry-index")
def retry_knowledge_document_index(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    document = retry_knowledge_document_index_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        user=user,
    )
    return envelope(
        document,
        get_trace_id(request),
    )


@router.delete("/api/knowledge/documents/{document_id}")
def delete_knowledge_document(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    result = delete_knowledge_document_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/search")
def search_knowledge(
    request: Request,
    payload: KnowledgeSearchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return knowledge_search_response(
        current_store=store(request),
        query_value=payload.query,
        top_k=payload.top_k,
        trace_id=get_trace_id(request),
        user=user,
    )


@router.get("/api/knowledge/deposits")
def list_knowledge_deposits(
    request: Request,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    return knowledge_deposit_list_response(
        current_store=store(request),
        status=status,
        trace_id=get_trace_id(request),
    )


@router.post("/api/knowledge/deposits/{deposit_id}/approve")
def approve_knowledge_deposit(
    deposit_id: str,
    request: Request,
    payload: KnowledgeDepositApproveRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    deposit = approve_knowledge_deposit_result(
        current_store=knowledge_write_store(store(request)),
        deposit_id=deposit_id,
        permission_roles=payload.permission_roles,
        title=payload.title,
        user=user,
    )
    return envelope(deposit, get_trace_id(request))


@router.post("/api/knowledge/deposits/{deposit_id}/reject")
def reject_knowledge_deposit(
    deposit_id: str,
    request: Request,
    payload: KnowledgeDepositRejectRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"knowledge_owner", "rd_owner"})
    deposit = reject_knowledge_deposit_result(
        current_store=knowledge_write_store(store(request)),
        deposit_id=deposit_id,
        reason=payload.reason,
        user=user,
    )
    return envelope(deposit, get_trace_id(request))
