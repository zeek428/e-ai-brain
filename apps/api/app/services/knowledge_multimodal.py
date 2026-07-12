from __future__ import annotations

import base64
import json
import os
from io import BytesIO
from typing import Any, Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class KnowledgeProcessingProvider(Protocol):
    def process(
        self,
        *,
        content: bytes,
        filename: str,
        mime_type: str,
        profile: dict[str, Any],
    ) -> dict[str, Any]: ...


def _credential_value(credential_ref: str | None) -> str | None:
    normalized = str(credential_ref or "").strip()
    if not normalized:
        return None
    if not normalized.startswith("env:"):
        raise ValueError("PROCESSING_PROFILE_CREDENTIAL_REF_INVALID")
    env_name = normalized.removeprefix("env:").strip()
    value = os.getenv(env_name, "")
    if not env_name or not value:
        raise ValueError("PROCESSING_PROFILE_CREDENTIAL_UNAVAILABLE")
    return value


def _provider_endpoint(profile: dict[str, Any]) -> str:
    provider_config = dict(profile.get("provider_config") or {})
    endpoint = str(provider_config.get("endpoint_url") or "").strip()
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
        raise ValueError("PROCESSING_PROFILE_ENDPOINT_INVALID")
    return endpoint


class HttpKnowledgeProcessingProvider:
    def process(
        self,
        *,
        content: bytes,
        filename: str,
        mime_type: str,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        provider_config = dict(profile.get("provider_config") or {})
        timeout_seconds = max(1, min(int(provider_config.get("timeout_seconds") or 120), 600))
        payload = json.dumps(
            {
                "capabilities": list(profile.get("capabilities") or []),
                "content_base64": base64.b64encode(content).decode("ascii"),
                "filename": filename,
                "mime_type": mime_type,
                "options": dict(provider_config.get("options") or {}),
            },
            ensure_ascii=True,
        ).encode()
        headers = {"Content-Type": "application/json"}
        credential = _credential_value(profile.get("credential_ref"))
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        request = Request(
            _provider_endpoint(profile),
            data=payload,
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            response_body = response.read(10 * 1024 * 1024 + 1)
            if len(response_body) > 10 * 1024 * 1024:
                raise ValueError("PROCESSING_PROVIDER_RESPONSE_TOO_LARGE")
            if int(getattr(response, "status", 200)) >= 400:
                raise ValueError("PROCESSING_PROVIDER_REQUEST_FAILED")
        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("PROCESSING_PROVIDER_RESPONSE_INVALID") from exc
        if not isinstance(decoded, dict):
            raise ValueError("PROCESSING_PROVIDER_RESPONSE_INVALID")
        return decoded


class BuiltinKnowledgeProcessingProvider:
    def process(
        self,
        *,
        content: bytes,
        filename: str,
        mime_type: str,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        if mime_type == "application/pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:  # pragma: no cover
                raise ValueError("PDF_PARSER_UNAVAILABLE") from exc
            try:
                reader = PdfReader(BytesIO(content))
                pages = [
                    {
                        "page_number": index,
                        "text": (page.extract_text() or "").strip(),
                    }
                    for index, page in enumerate(reader.pages, start=1)
                ]
            except Exception as exc:  # noqa: BLE001
                raise ValueError("PDF_PARSE_FAILED") from exc
            if not any(page["text"] for page in pages):
                raise ValueError("MULTIMODAL_PROVIDER_REQUIRED")
            return {
                "pages": pages,
                "provider_metadata": {"provider": "builtin", "source": filename},
            }
        if mime_type.startswith("text/") or mime_type == "application/json":
            text = content.decode("utf-8", errors="replace").strip()
            if not text:
                raise ValueError("NO_INDEXABLE_CONTENT")
            return {
                "pages": [{"page_number": 1, "text": text}],
                "provider_metadata": {"provider": "builtin", "source": filename},
            }
        raise ValueError("MULTIMODAL_PROVIDER_REQUIRED")


def resolve_knowledge_processing_provider(
    profile: dict[str, Any],
) -> KnowledgeProcessingProvider:
    provider_type = str(profile.get("provider_type") or "builtin")
    if provider_type == "builtin":
        return BuiltinKnowledgeProcessingProvider()
    if provider_type in {
        "gotenberg",
        "http",
        "mineru",
        "multimodal_gateway",
        "paddleocr",
    }:
        return HttpKnowledgeProcessingProvider()
    raise ValueError("PROCESSING_PROFILE_PROVIDER_UNSUPPORTED")


def _number(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _bounding_boxes(block: dict[str, Any]) -> list[Any]:
    value = block.get("bounding_boxes")
    if isinstance(value, list):
        return value
    value = block.get("bounding_box") or block.get("bbox")
    return [value] if isinstance(value, list) else []


def _table_markdown(table: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(table, dict):
        return str(table or "").strip(), {}
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    row_dicts = [dict(row) for row in rows if isinstance(row, dict)]
    columns = [str(item) for item in table.get("columns") or [] if str(item)]
    if not columns:
        columns = sorted({str(key) for row in row_dicts for key in row})
    if not columns or not row_dicts:
        return str(table.get("markdown") or table.get("text") or "").strip(), {
            "columns": columns,
            "rows": row_dicts,
        }
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in row_dicts
    ]
    return "\n".join([header, divider, *body]), {"columns": columns, "rows": row_dicts}


def _block_modality(block: dict[str, Any]) -> str:
    modality = str(block.get("modality") or block.get("type") or "text").lower()
    if modality in {"figure", "image", "picture"}:
        return "image"
    if modality in {"table", "spreadsheet"}:
        return "table"
    if modality in {"layout", "region"}:
        return "layout"
    if modality == "multimodal":
        return "multimodal"
    return "text"


def build_multimodal_parse_result(
    *,
    filename: str,
    profile: dict[str, Any],
    provider_result: dict[str, Any],
) -> dict[str, Any]:
    pages = provider_result.get("pages")
    if not isinstance(pages, list):
        pages = [{"page_number": 1, "text": provider_result.get("text", "")}]
    provider_metadata = dict(provider_result.get("provider_metadata") or {})
    provider_metadata.setdefault("provider_type", profile.get("provider_type"))
    markdown_sections: list[str] = []
    source_map: list[dict[str, Any]] = []
    normalized_pages: list[dict[str, Any]] = []
    normalized_tables: list[dict[str, Any]] = []
    image_annotations: list[dict[str, Any]] = []
    sidecar_assets: list[dict[str, Any]] = []
    visual_embeddings: list[dict[str, Any]] = []
    modalities: set[str] = set()

    for page_index, raw_page in enumerate(pages, start=1):
        if not isinstance(raw_page, dict):
            continue
        page_number = _number(raw_page.get("page_number") or raw_page.get("page"), page_index)
        page_sections: list[str] = []
        page_text = str(raw_page.get("text") or "").strip()
        if page_text:
            page_sections.append(page_text)
            modalities.add("text")
            source_map.append(
                {
                    "match_text": page_text,
                    "metadata": {
                        "modality": "text",
                        "page_number": page_number,
                        "provider_metadata": provider_metadata,
                        "source_asset_type": "ocr_json",
                        "source_kind": "ocr_page",
                    },
                }
            )
        blocks = raw_page.get("blocks") if isinstance(raw_page.get("blocks"), list) else []
        normalized_blocks: list[dict[str, Any]] = []
        page_boxes: list[Any] = []
        for block_index, raw_block in enumerate(blocks, start=1):
            if not isinstance(raw_block, dict):
                continue
            block = dict(raw_block)
            modality = _block_modality(block)
            modalities.add(modality)
            boxes = _bounding_boxes(block)
            page_boxes.extend(boxes)
            text = str(
                block.get("text")
                or block.get("description")
                or block.get("caption")
                or block.get("markdown")
                or ""
            ).strip()
            table_metadata: dict[str, Any] = {}
            if modality == "table":
                table_markdown, table_metadata = _table_markdown(block.get("table") or block)
                text = table_markdown or text
                if text:
                    normalized_tables.append(
                        {
                            **table_metadata,
                            "bounding_boxes": boxes,
                            "page_number": page_number,
                            "table_index": len(normalized_tables) + 1,
                        }
                    )
            if not text:
                continue
            label = {
                "image": "Image",
                "layout": "Layout",
                "multimodal": "Multimodal",
                "table": "Table",
                "text": "Text",
            }[modality]
            page_sections.append(f"### {label} {block_index}\n\n{text}")
            metadata = {
                "bounding_boxes": boxes,
                "confidence": block.get("confidence"),
                "modality": modality,
                "page_number": page_number,
                "provider_metadata": provider_metadata,
                "source_kind": f"{modality}_block",
                "source_asset_type": {
                    "image": "image_annotation_json",
                    "layout": "layout_json",
                    "multimodal": "layout_json",
                    "table": "table_json",
                    "text": "ocr_json",
                }[modality],
                **table_metadata,
            }
            source_map.append({"match_text": text, "metadata": metadata})
            normalized_block = {
                "bounding_boxes": boxes,
                "confidence": block.get("confidence"),
                "modality": modality,
                "text": text,
            }
            normalized_blocks.append(normalized_block)
            if modality == "image":
                image_annotations.append(
                    {**normalized_block, "page_number": page_number}
                )
        if page_sections:
            markdown_sections.append(
                f"## Page {page_number}\n\n" + "\n\n".join(page_sections)
            )
        normalized_page = {
            "blocks": normalized_blocks,
            "page_number": page_number,
            "text": page_text,
        }
        normalized_pages.append(normalized_page)
        sidecar_assets.append(
            {
                "asset_type": "layout_json",
                "bounding_boxes": page_boxes,
                "content": json.dumps(normalized_page, ensure_ascii=False, indent=2),
                "filename": f"{filename}.page-{page_number}.layout.json",
                "mime_type": "application/json",
                "page_number": page_number,
                "provider_metadata": provider_metadata,
            }
        )

    if not markdown_sections:
        raise ValueError("MULTIMODAL_CONTENT_EMPTY")
    sidecar_assets.append(
        {
            "asset_type": "ocr_json",
            "content": json.dumps({"pages": normalized_pages}, ensure_ascii=False, indent=2),
            "filename": f"{filename}.ocr.json",
            "mime_type": "application/json",
            "provider_metadata": provider_metadata,
        }
    )
    if normalized_tables:
        sidecar_assets.append(
            {
                "asset_type": "table_json",
                "content": json.dumps(
                    {"tables": normalized_tables},
                    ensure_ascii=False,
                    indent=2,
                ),
                "filename": f"{filename}.tables.json",
                "mime_type": "application/json",
                "provider_metadata": provider_metadata,
            }
        )
    if image_annotations:
        sidecar_assets.append(
            {
                "asset_type": "image_annotation_json",
                "content": json.dumps(
                    {"images": image_annotations},
                    ensure_ascii=False,
                    indent=2,
                ),
                "filename": f"{filename}.images.json",
                "mime_type": "application/json",
                "provider_metadata": provider_metadata,
            }
        )
    raw_visual_embeddings = provider_result.get("image_embeddings")
    if isinstance(raw_visual_embeddings, list):
        for raw_embedding in raw_visual_embeddings:
            if not isinstance(raw_embedding, dict):
                continue
            embedding = raw_embedding.get("embedding")
            if not isinstance(embedding, list) or not embedding or len(embedding) > 4096:
                continue
            try:
                vector = [float(value) for value in embedding]
            except (TypeError, ValueError):
                continue
            visual_embeddings.append(
                {
                    "bounding_box": raw_embedding.get("bounding_box") or raw_embedding.get("bbox"),
                    "embedding": vector,
                    "page_number": raw_embedding.get("page_number") or raw_embedding.get("page"),
                }
            )
    return {
        "asset_type": "parsed_markdown",
        "content": "\n\n".join(markdown_sections),
        "filename": f"{filename}.multimodal.md",
        "metadata": {
            "modalities": sorted(modalities),
            "page_count": len(normalized_pages),
            "parser_engine": "multimodal",
            "processing_profile_id": profile.get("id"),
            "provider_metadata": provider_metadata,
        },
        "mime_type": "text/markdown",
        "provider_metadata": provider_metadata,
        "sidecar_assets": sidecar_assets,
        "source_map": source_map,
        "visual_embeddings": visual_embeddings,
    }


def process_multimodal_asset(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    provider = resolve_knowledge_processing_provider(profile)
    provider_result = provider.process(
        content=content,
        filename=filename,
        mime_type=mime_type,
        profile=profile,
    )
    return build_multimodal_parse_result(
        filename=filename,
        profile=profile,
        provider_result=provider_result,
    )
