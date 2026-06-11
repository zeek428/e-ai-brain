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
from app.services.knowledge_management import (
    asset_preview_result,
    create_knowledge_folder_result,
    create_knowledge_space_result,
    list_knowledge_document_assets_result,
    list_knowledge_folders_result,
    list_knowledge_import_jobs_result,
    list_knowledge_spaces_result,
    update_knowledge_space_members_result,
    upload_knowledge_document_result,
)
from app.services.knowledge_search import knowledge_search_response

router = APIRouter(tags=["knowledge"])


class KnowledgeDocumentRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "manual"
    product_id: str | None = None
    knowledge_space_id: str | None = None
    folder_id: str | None = None
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])
    tags: list[str] = Field(default_factory=list)


class KnowledgeDocumentPatchRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    doc_type: str | None = None
    product_id: str | None = None
    knowledge_space_id: str | None = None
    folder_id: str | None = None
    permission_roles: list[str] | None = None
    tags: list[str] | None = None
    index_status: str | None = None
    index_error: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 8
    knowledge_space_id: str | None = None


class KnowledgeSpaceRequest(BaseModel):
    code: str
    name: str
    description: str = ""


class KnowledgeSpaceMember(BaseModel):
    user_id: str
    space_role: str = "reader"


class KnowledgeSpaceMembersRequest(BaseModel):
    members: list[KnowledgeSpaceMember] = Field(default_factory=list)


class KnowledgeFolderRequest(BaseModel):
    name: str
    parent_folder_id: str | None = None


class KnowledgeDocumentUploadRequest(BaseModel):
    knowledge_space_id: str
    folder_id: str | None = None
    title: str
    filename: str
    content_base64: str
    mime_type: str = "application/octet-stream"
    doc_type: str = "manual"
    tags: list[str] = Field(default_factory=list)


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
    knowledge_space_id: str | None = None,
    folder_id: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return knowledge_document_list_response(
        current_store=store(request),
        doc_type=doc_type,
        folder_id=folder_id,
        index_status=index_status,
        knowledge_space_id=knowledge_space_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
        permission_role=permission_role,
        request=request,
        sort_by=sort_by,
        sort_order=sort_order,
        user=user,
    )


@router.get("/api/knowledge/spaces")
def list_knowledge_spaces(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_knowledge_spaces_result(
            current_store=knowledge_write_store(store(request)),
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/knowledge/spaces")
def create_knowledge_space(
    request: Request,
    payload: KnowledgeSpaceRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    space = create_knowledge_space_result(
        code=payload.code,
        current_store=knowledge_write_store(store(request)),
        description=payload.description,
        name=payload.name,
        user=user,
    )
    return envelope(space, get_trace_id(request))


@router.put("/api/knowledge/spaces/{space_id}/members")
def update_knowledge_space_members(
    space_id: str,
    request: Request,
    payload: KnowledgeSpaceMembersRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = update_knowledge_space_members_result(
        current_store=knowledge_write_store(store(request)),
        members=[member.model_dump() for member in payload.members],
        space_id=space_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/spaces/{space_id}/folders")
def list_knowledge_folders(
    space_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_knowledge_folders_result(
            current_store=knowledge_write_store(store(request)),
            space_id=space_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/knowledge/spaces/{space_id}/folders")
def create_knowledge_folder(
    space_id: str,
    request: Request,
    payload: KnowledgeFolderRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    folder = create_knowledge_folder_result(
        current_store=knowledge_write_store(store(request)),
        name=payload.name,
        parent_folder_id=payload.parent_folder_id,
        space_id=space_id,
        user=user,
    )
    return envelope(folder, get_trace_id(request))


@router.post("/api/knowledge/documents/upload")
def upload_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentUploadRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = upload_knowledge_document_result(
        content_base64=payload.content_base64,
        current_store=knowledge_write_store(store(request)),
        doc_type=payload.doc_type,
        filename=payload.filename,
        folder_id=payload.folder_id,
        knowledge_space_id=payload.knowledge_space_id,
        mime_type=payload.mime_type,
        tags=payload.tags,
        title=payload.title,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/documents/{document_id}/assets")
def list_knowledge_document_assets(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_knowledge_document_assets_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/assets/{asset_id}/preview")
def preview_knowledge_asset(
    asset_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = asset_preview_result(
        asset_id=asset_id,
        current_store=knowledge_write_store(store(request)),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/import-jobs")
def list_knowledge_import_jobs(
    request: Request,
    document_id: str | None = None,
    knowledge_space_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_knowledge_import_jobs_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        knowledge_space_id=knowledge_space_id,
        status=status,
        user=user,
    )
    return envelope(result, get_trace_id(request))


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
        folder_id=payload.folder_id,
        knowledge_space_id=payload.knowledge_space_id,
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
        knowledge_space_id=payload.knowledge_space_id,
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
