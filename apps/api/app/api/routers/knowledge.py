from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import (
    CurrentUser,
    require_any_permission_or_roles,
    require_permissions,
    store,
)
from app.core.config import get_settings
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
from app.services.knowledge_import_worker import (
    enqueue_knowledge_import_job,
    knowledge_import_worker_status,
)
from app.services.knowledge_index_health import knowledge_index_health_response
from app.services.knowledge_management import (
    activate_knowledge_chunk_set_result,
    asset_preview_result,
    batch_move_knowledge_documents_result,
    cancel_knowledge_import_job_result,
    create_knowledge_folder_result,
    create_knowledge_space_result,
    create_knowledge_upload_presign_result,
    list_knowledge_chunk_sets_result,
    list_knowledge_chunks_result,
    list_knowledge_document_assets_result,
    list_knowledge_folders_result,
    list_knowledge_import_jobs_result,
    list_knowledge_spaces_result,
    patch_knowledge_folder_result,
    reparse_knowledge_document_result,
    retry_knowledge_import_job_result,
    run_knowledge_import_job_result,
    update_knowledge_space_members_result,
    upload_knowledge_document_bytes_result,
    upload_knowledge_document_result,
)
from app.services.knowledge_multimodal_governance import (
    create_processing_profile_result,
    list_citation_feedback_result,
    list_document_versions_result,
    list_processing_profiles_result,
    list_staleness_result,
    record_citation_feedback_result,
    scan_staleness_result,
    update_processing_profile_result,
)
from app.services.knowledge_quality import (
    knowledge_quality_metrics_response,
    record_knowledge_quality_event,
)
from app.services.knowledge_rag import knowledge_rag_response
from app.services.knowledge_search import knowledge_search_response
from app.services.knowledge_visual_search import (
    visual_search_response,
    visual_search_with_image_response,
)

router = APIRouter(tags=["knowledge"])
settings = get_settings()
KNOWLEDGE_DEPOSIT_DECIDE_PERMISSION = "knowledge.deposit.decide"
KNOWLEDGE_MANAGE_PERMISSION = "knowledge.manage"


class KnowledgeVisualSearchRequest(BaseModel):
    query_embedding: list[float] = Field(min_length=1, max_length=4096)


def _require_knowledge_manage(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(
        user,
        {KNOWLEDGE_MANAGE_PERMISSION},
        {"knowledge_owner", "rd_owner"},
    )


def _request_started_at(request: Request) -> float | None:
    return getattr(request.state, "started_at", None)


@router.post("/api/knowledge/search/visual")
def search_knowledge_visually(
    payload: KnowledgeVisualSearchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"knowledge.read"}, {"knowledge_owner", "rd_owner"})
    return envelope(
        visual_search_response(
            current_store=store(request),
            query_embedding=payload.query_embedding,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/knowledge/search/visual-file")
async def search_knowledge_visually_with_file(
    request: Request,
    file: Annotated[UploadFile, File()],
    processing_profile_id: Annotated[str, Form()],
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"knowledge.read"}, {"knowledge_owner", "rd_owner"})
    content = await file.read(10 * 1024 * 1024 + 1)
    return envelope(
        visual_search_with_image_response(
            content=content,
            current_store=store(request),
            filename=file.filename or "visual-query",
            mime_type=file.content_type or "application/octet-stream",
            processing_profile_id=processing_profile_id,
            user=user,
        ),
        get_trace_id(request),
    )


def _parse_form_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


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


class KnowledgeRagRequest(BaseModel):
    query: str
    top_k: int = 6
    knowledge_space_id: str | None = None


class KnowledgeQualityFeedbackRequest(BaseModel):
    related_event_id: str
    feedback_value: str
    feedback_comment: str | None = None
    citation_chunk_id: str | None = None
    citation_document_id: str | None = None


class KnowledgeCitationClickRequest(BaseModel):
    related_event_id: str
    citation_chunk_id: str | None = None
    citation_document_id: str | None = None


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


class KnowledgeFolderPatchRequest(BaseModel):
    name: str | None = None
    parent_folder_id: str | None = None
    sort_order: int | None = None
    status: str | None = None


class KnowledgeDocumentUploadRequest(BaseModel):
    knowledge_space_id: str
    folder_id: str | None = None
    title: str
    filename: str
    content_base64: str
    mime_type: str = "application/octet-stream"
    doc_type: str = "manual"
    parser_engine: str | None = None
    chunk_strategy: str | None = None
    processing_profile_id: str | None = None
    product_id: str | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)
    tags: list[str] = Field(default_factory=list)


class KnowledgeUploadPresignRequest(BaseModel):
    content_length: int | None = Field(default=None, ge=1)
    filename: str
    knowledge_space_id: str
    mime_type: str = "application/octet-stream"


class KnowledgeDocumentReparseRequest(BaseModel):
    parser_engine: str | None = None
    chunk_strategy: str | None = None
    processing_profile_id: str | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class KnowledgeProcessingProfileRequest(BaseModel):
    name: str
    product_id: str | None = None
    provider_type: str
    provider_config: dict[str, Any] = Field(default_factory=dict)
    credential_ref: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class KnowledgeProcessingProfilePatchRequest(BaseModel):
    name: str | None = None
    provider_config: dict[str, Any] | None = None
    credential_ref: str | None = None
    capabilities: list[str] | None = None
    status: str | None = None


class KnowledgeDocumentsBatchMoveRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    folder_id: str | None = None


class KnowledgeDepositApproveRequest(BaseModel):
    folder_id: str | None = None
    knowledge_space_id: str
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


@router.get("/api/knowledge/index-health")
def knowledge_index_health(
    request: Request,
    keyword: str | None = None,
    doc_type: str | None = None,
    index_status: str | None = None,
    permission_role: str | None = None,
    knowledge_space_id: str | None = None,
    folder_id: str | None = None,
    issue_limit: int = Query(default=10, ge=1, le=50),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return knowledge_index_health_response(
        current_store=store(request),
        doc_type=doc_type,
        folder_id=folder_id,
        index_status=index_status,
        issue_limit=issue_limit,
        knowledge_space_id=knowledge_space_id,
        keyword=keyword,
        permission_role=permission_role,
        request=request,
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


@router.get("/api/knowledge/processing-profiles")
def list_knowledge_processing_profiles(
    request: Request,
    product_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
    result = list_processing_profiles_result(
        current_store=knowledge_write_store(store(request)),
        product_id=product_id,
        status=status,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/processing-profiles")
def create_knowledge_processing_profile(
    request: Request,
    payload: KnowledgeProcessingProfileRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
    result = create_processing_profile_result(
        capabilities=payload.capabilities,
        credential_ref=payload.credential_ref,
        current_store=knowledge_write_store(store(request)),
        name=payload.name,
        product_id=payload.product_id,
        provider_config=payload.provider_config,
        provider_type=payload.provider_type,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/api/knowledge/processing-profiles/{profile_id}")
def update_knowledge_processing_profile(
    profile_id: str,
    request: Request,
    payload: KnowledgeProcessingProfilePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
    result = update_processing_profile_result(
        capabilities=payload.capabilities,
        credential_ref=payload.credential_ref,
        credential_ref_set="credential_ref" in payload.model_fields_set,
        current_store=knowledge_write_store(store(request)),
        name=payload.name,
        profile_id=profile_id,
        provider_config=payload.provider_config,
        status=payload.status,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/staleness")
def list_knowledge_staleness(
    request: Request,
    knowledge_space_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_staleness_result(
        current_store=knowledge_write_store(store(request)),
        knowledge_space_id=knowledge_space_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/staleness/scan")
def scan_knowledge_staleness(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
    result = scan_staleness_result(
        current_store=knowledge_write_store(store(request)),
        user=user,
    )
    return envelope(result, get_trace_id(request))


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


@router.patch("/api/knowledge/folders/{folder_id}")
def patch_knowledge_folder(
    folder_id: str,
    request: Request,
    payload: KnowledgeFolderPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    folder = patch_knowledge_folder_result(
        current_store=knowledge_write_store(store(request)),
        folder_id=folder_id,
        name=payload.name,
        parent_folder_id=payload.parent_folder_id,
        parent_folder_id_set="parent_folder_id" in payload.model_fields_set,
        sort_order=payload.sort_order,
        status=payload.status,
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
        parser_engine=payload.parser_engine,
        chunk_strategy=payload.chunk_strategy,
        processing_profile_id=payload.processing_profile_id,
        product_id=payload.product_id,
        expires_in_days=payload.expires_in_days,
        tags=payload.tags,
        title=payload.title,
        user=user,
    )
    enqueue_knowledge_import_job(
        request.app,
        job_id=result["import_job"]["id"],
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/documents/upload-file")
async def upload_knowledge_document_file(
    request: Request,
    file: Annotated[UploadFile, File()],
    knowledge_space_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    folder_id: Annotated[str | None, Form()] = None,
    doc_type: Annotated[str, Form()] = "manual",
    parser_engine: Annotated[str | None, Form()] = None,
    chunk_strategy: Annotated[str | None, Form()] = None,
    processing_profile_id: Annotated[str | None, Form()] = None,
    product_id: Annotated[str | None, Form()] = None,
    expires_in_days: Annotated[int | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    max_bytes = get_settings().knowledge_upload_max_bytes
    content = await file.read(max_bytes + 1)
    result = upload_knowledge_document_bytes_result(
        content=content,
        current_store=knowledge_write_store(store(request)),
        doc_type=doc_type,
        filename=file.filename or title,
        folder_id=folder_id,
        knowledge_space_id=knowledge_space_id,
        mime_type=file.content_type or "application/octet-stream",
        parser_engine=parser_engine,
        chunk_strategy=chunk_strategy,
        processing_profile_id=processing_profile_id,
        product_id=product_id,
        expires_in_days=expires_in_days,
        tags=_parse_form_tags(tags),
        title=title,
        user=user,
    )
    enqueue_knowledge_import_job(
        request.app,
        job_id=result["import_job"]["id"],
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/uploads/presign")
def create_knowledge_upload_presign(
    request: Request,
    payload: KnowledgeUploadPresignRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = create_knowledge_upload_presign_result(
        content_length=payload.content_length,
        current_store=knowledge_write_store(store(request)),
        filename=payload.filename,
        knowledge_space_id=payload.knowledge_space_id,
        mime_type=payload.mime_type,
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


@router.get("/api/knowledge/documents/{document_id}/versions")
def list_knowledge_document_versions(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_document_versions_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/documents/{document_id}/citation-feedback")
def list_knowledge_document_citation_feedback(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_citation_feedback_result(
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


@router.get("/api/knowledge/import-worker/status")
def get_knowledge_import_worker_status(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
    return envelope(
        knowledge_import_worker_status(request.app, settings),
        get_trace_id(request),
    )


@router.post("/api/knowledge/import-jobs/{job_id}/run")
def run_knowledge_import_job(
    job_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = run_knowledge_import_job_result(
        current_store=knowledge_write_store(store(request)),
        job_id=job_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/import-jobs/{job_id}/retry")
def retry_knowledge_import_job(
    job_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = retry_knowledge_import_job_result(
        current_store=knowledge_write_store(store(request)),
        job_id=job_id,
        user=user,
    )
    enqueue_knowledge_import_job(
        request.app,
        job_id=result["import_job"]["id"],
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/import-jobs/{job_id}/cancel")
def cancel_knowledge_import_job(
    job_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = cancel_knowledge_import_job_result(
        current_store=knowledge_write_store(store(request)),
        job_id=job_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/documents/{document_id}/chunk-sets")
def list_knowledge_chunk_sets(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_knowledge_chunk_sets_result(
        current_store=knowledge_write_store(store(request)),
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/knowledge/documents/{document_id}/chunks")
def list_knowledge_chunks(
    document_id: str,
    request: Request,
    chunk_set_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_knowledge_chunks_result(
        current_store=knowledge_write_store(store(request)),
        chunk_set_id=chunk_set_id,
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/documents/{document_id}/chunk-sets/{chunk_set_id}/activate")
def activate_knowledge_chunk_set(
    document_id: str,
    chunk_set_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = activate_knowledge_chunk_set_result(
        current_store=knowledge_write_store(store(request)),
        chunk_set_id=chunk_set_id,
        document_id=document_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/documents/{document_id}/reparse")
def reparse_knowledge_document(
    document_id: str,
    request: Request,
    payload: KnowledgeDocumentReparseRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = reparse_knowledge_document_result(
        current_store=knowledge_write_store(store(request)),
        chunk_strategy=payload.chunk_strategy,
        document_id=document_id,
        parser_engine=payload.parser_engine,
        processing_profile_id=payload.processing_profile_id,
        expires_in_days=payload.expires_in_days,
        user=user,
    )
    enqueue_knowledge_import_job(
        request.app,
        job_id=result["import_job"]["id"],
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/documents/batch-move")
def batch_move_knowledge_documents(
    request: Request,
    payload: KnowledgeDocumentsBatchMoveRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_move_knowledge_documents_result(
        current_store=knowledge_write_store(store(request)),
        document_ids=payload.document_ids,
        folder_id=payload.folder_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/knowledge/documents")
def create_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_knowledge_manage(user)
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
    _require_knowledge_manage(user)
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
    _require_knowledge_manage(user)
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
    _require_knowledge_manage(user)
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


@router.post("/api/knowledge/rag")
def ask_knowledge_rag(
    request: Request,
    payload: KnowledgeRagRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return knowledge_rag_response(
        current_store=store(request),
        knowledge_space_id=payload.knowledge_space_id,
        query_value=payload.query,
        top_k=payload.top_k,
        trace_id=get_trace_id(request),
        user=user,
    )


@router.get("/api/knowledge/quality/metrics")
def get_knowledge_quality_metrics(
    request: Request,
    event_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    since_days: int = Query(default=30, ge=1, le=365),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"knowledge.quality.read", KNOWLEDGE_MANAGE_PERMISSION},
        {"knowledge_owner", "rd_owner"},
    )
    return knowledge_quality_metrics_response(
        store(request),
        event_type=event_type,
        limit=limit,
        since_days=since_days,
        trace_id=get_trace_id(request),
    )


@router.post("/api/knowledge/quality/feedback")
def create_knowledge_quality_feedback(
    request: Request,
    payload: KnowledgeQualityFeedbackRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = knowledge_write_store(store(request))
    event = record_knowledge_quality_event(
        current_store,
        citation_chunk_id=payload.citation_chunk_id,
        citation_document_id=payload.citation_document_id,
        event_type="feedback",
        feedback_comment=payload.feedback_comment,
        feedback_value=payload.feedback_value,
        related_event_id=payload.related_event_id,
        trace_id=get_trace_id(request),
        user=user,
    )
    if payload.citation_document_id:
        citation_feedback = record_citation_feedback_result(
            chunk_id=payload.citation_chunk_id,
            comment=payload.feedback_comment,
            current_store=current_store,
            document_id=payload.citation_document_id,
            feedback_value=payload.feedback_value,
            related_event_id=payload.related_event_id,
            user=user,
        )
        event = {
            **event,
            "citation_feedback_id": citation_feedback["id"],
            "document_version_id": citation_feedback.get("document_version_id"),
        }
    return envelope(event, get_trace_id(request))


@router.post("/api/knowledge/quality/citation-click")
def create_knowledge_citation_click(
    request: Request,
    payload: KnowledgeCitationClickRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    event = record_knowledge_quality_event(
        store(request),
        citation_chunk_id=payload.citation_chunk_id,
        citation_count=1,
        citation_document_id=payload.citation_document_id,
        event_type="citation_click",
        related_event_id=payload.related_event_id,
        trace_id=get_trace_id(request),
        user=user,
    )
    return envelope(event, get_trace_id(request))


@router.get("/api/knowledge/deposits")
def list_knowledge_deposits(
    request: Request,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = Query(default="desc"),
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {KNOWLEDGE_DEPOSIT_DECIDE_PERMISSION})
    return knowledge_deposit_list_response(
        current_store=store(request),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=_request_started_at(request),
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
    require_permissions(user, {KNOWLEDGE_DEPOSIT_DECIDE_PERMISSION})
    deposit = approve_knowledge_deposit_result(
        current_store=knowledge_write_store(store(request)),
        deposit_id=deposit_id,
        folder_id=payload.folder_id,
        knowledge_space_id=payload.knowledge_space_id,
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
    require_permissions(user, {KNOWLEDGE_DEPOSIT_DECIDE_PERMISSION})
    deposit = reject_knowledge_deposit_result(
        current_store=knowledge_write_store(store(request)),
        deposit_id=deposit_id,
        reason=payload.reason,
        user=user,
    )
    return envelope(deposit, get_trace_id(request))
