from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_embeddings_with_context,
)


def split_knowledge_content(content: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", content) if part.strip()]
    if not paragraphs:
        paragraphs = [content.strip()]
    chunks: list[str] = []
    max_chars = 1200
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunk = paragraph[start : start + max_chars].strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def split_markdown_parent_child_content(content: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_heading = "文档"
    current_lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if line.startswith("#"):
            if current_lines:
                sections.append(
                    {"heading": current_heading, "body": "\n".join(current_lines).strip()}
                )
                current_lines = []
            current_heading = line.lstrip("#").strip() or current_heading
            current_lines.append(line)
            continue
        current_lines.append(line)
    if current_lines:
        sections.append({"heading": current_heading, "body": "\n".join(current_lines).strip()})
    if not sections:
        sections = [{"heading": "文档", "body": content.strip()}]

    descriptors: list[dict[str, Any]] = []
    for section_index, section in enumerate(sections, start=1):
        body = section["body"].strip()
        if not body:
            continue
        parent_local_id = f"parent-{section_index}"
        descriptors.append(
            {
                "content": body,
                "local_id": parent_local_id,
                "metadata": {
                    "chunk_role": "parent",
                    "heading": section["heading"],
                    "section_index": section_index,
                },
            }
        )
        child_parts = split_knowledge_content(body)
        for child_index, child_content in enumerate(child_parts, start=1):
            descriptors.append(
                {
                    "content": child_content,
                    "local_id": f"child-{section_index}-{child_index}",
                    "metadata": {
                        "chunk_role": "child",
                        "heading": section["heading"],
                        "parent_content": body,
                        "section_index": section_index,
                    },
                    "parent_local_id": parent_local_id,
                }
            )
    return descriptors


def split_regex_section_content(content: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?im)^(?P<separator>\s*(?:-{3,}|\*{3,}|_{3,}|#{1,6}\s+.+|(?:第[一二三四五六七八九十百千\d]+[章节篇部分]\s*[:：]?.*)|(?:section|chapter)\s+\d+(?:[.:：].*)?))$"
    )
    matches = list(pattern.finditer(content))
    sections: list[dict[str, Any]] = []
    previous_start = 0
    previous_title = "文档开头"
    previous_separator = "document_start"
    section_index = 1

    for match in matches:
        body = content[previous_start : match.start()].strip()
        if body:
            sections.append(
                {
                    "body": body,
                    "section_index": section_index,
                    "separator": previous_separator,
                    "title": previous_title,
                }
            )
            section_index += 1
        previous_start = match.end()
        previous_title = match.group("separator").strip()
        previous_separator = "regex_separator"

    trailing_body = content[previous_start:].strip()
    if trailing_body:
        sections.append(
            {
                "body": trailing_body,
                "section_index": section_index,
                "separator": previous_separator,
                "title": previous_title,
            }
        )

    if not sections:
        sections = [
            {
                "body": chunk,
                "section_index": index,
                "separator": "blank_line",
                "title": f"片段 {index}",
            }
            for index, chunk in enumerate(split_knowledge_content(content), start=1)
        ]

    descriptors: list[dict[str, Any]] = []
    for section in sections:
        section_body = str(section["body"]).strip()
        if not section_body:
            continue
        for part_index, chunk_content in enumerate(
            split_knowledge_content(section_body),
            start=1,
        ):
            descriptors.append(
                {
                    "content": chunk_content,
                    "local_id": f"regex-{section['section_index']}-{part_index}",
                    "metadata": {
                        "chunk_role": "regex_section",
                        "section_index": section["section_index"],
                        "section_title": section["title"],
                        "split_pattern": section["separator"],
                    },
                }
            )
    return descriptors


def split_knowledge_content_descriptors(
    content: str,
    *,
    chunk_strategy: str = "simple_text",
) -> list[dict[str, Any]]:
    if chunk_strategy == "parent_child":
        return split_markdown_parent_child_content(content)
    if chunk_strategy == "regex_section":
        return split_regex_section_content(content)
    return [
        {
            "content": chunk,
            "local_id": f"chunk-{index}",
            "metadata": {"chunk_role": "chunk"},
        }
        for index, chunk in enumerate(split_knowledge_content(content), start=1)
    ]


def chunk_descriptor_contents(chunks: list[dict[str, Any]]) -> list[str]:
    return [str(chunk.get("content") or "") for chunk in chunks]


def build_knowledge_chunks(
    document: dict[str, Any],
    chunks: list[str] | list[dict[str, Any]],
    *,
    embeddings: list[list[float]] | None = None,
    embedding_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    permission_roles = list(document.get("permission_roles", ["admin"]))
    now = datetime.now(UTC).isoformat()
    records: list[dict[str, Any]] = []
    normalized_chunks: list[dict[str, Any]] = [
        {"content": chunk, "local_id": f"chunk-{index}", "metadata": {"chunk_role": "chunk"}}
        if isinstance(chunk, str)
        else chunk
        for index, chunk in enumerate(chunks, start=1)
    ]
    local_id_to_chunk_id = {
        chunk.get("local_id", f"chunk-{index}"): f"{document['id']}_chunk_{index:03d}"
        for index, chunk in enumerate(normalized_chunks, start=1)
    }
    for chunk_index, chunk_descriptor in enumerate(normalized_chunks, start=1):
        content = str(chunk_descriptor.get("content") or "")
        chunk_id = f"{document['id']}_chunk_{chunk_index:03d}"
        metadata = {
            "doc_type": document.get("doc_type", "manual"),
            "product_id": document.get("product_id"),
            "tags": list(document.get("tags", [])),
            "title": document["title"],
            **dict(chunk_descriptor.get("metadata") or {}),
        }
        if embeddings is not None and embedding_context is not None:
            metadata.update(
                {
                    key: value
                    for key, value in {
                        **embedding_context,
                        "embedding_created_at": datetime.now(UTC).isoformat(),
                    }.items()
                    if value is not None
                }
            )
        record = {
                "chunk_index": chunk_index,
                "content": content,
                "document_id": document["id"],
                "embedding": embeddings[chunk_index - 1] if embeddings is not None else None,
                "id": chunk_id,
                "metadata": metadata,
                "permission_roles": permission_roles,
                "permission_scope": {"roles": permission_roles},
                "created_at": now,
                "updated_at": now,
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            }
        parent_local_id = chunk_descriptor.get("parent_local_id")
        if parent_local_id:
            record["parent_chunk_id"] = local_id_to_chunk_id.get(str(parent_local_id))
        records.append(record)
    return records


def knowledge_index_failed_result(
    document: dict[str, Any],
    error: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    updated_document["chunk_count"] = 0
    updated_document["index_error"] = error.strip() or "index_error is required"
    updated_document["index_status"] = "index_failed"
    updated_document["vector_index_error"] = None
    return updated_document, []


def knowledge_text_indexed_result(
    document: dict[str, Any],
    chunks: list[str] | list[dict[str, Any]],
    *,
    vector_error: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = build_knowledge_chunks(updated_document, chunks)
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "text_indexed"
    updated_document["index_error"] = vector_error
    updated_document["vector_index_error"] = vector_error
    return updated_document, chunk_records


def knowledge_vector_indexed_result(
    document: dict[str, Any],
    chunks: list[str] | list[dict[str, Any]],
    embeddings: list[list[float]],
    embedding_context: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = build_knowledge_chunks(
        updated_document,
        chunks,
        embeddings=embeddings,
        embedding_context=embedding_context,
    )
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "vector_indexed"
    updated_document["index_error"] = None
    updated_document["vector_index_error"] = None
    return updated_document, chunk_records


def replace_knowledge_chunks_result(
    current_store: Any,
    document: dict[str, Any],
    *,
    attempt_vector: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    chunks = split_knowledge_content_descriptors(
        document["content"],
        chunk_strategy=document.get("chunk_strategy", "simple_text"),
    )
    if not chunks:
        return knowledge_index_failed_result(document, "NO_INDEXABLE_CONTENT")
    if not attempt_vector:
        return knowledge_text_indexed_result(document, chunks)
    try:
        embeddings, embedding_context = call_model_gateway_embeddings_with_context(
            current_store,
            chunk_descriptor_contents(chunks),
        )
    except ModelGatewayConfigError as exc:
        return knowledge_text_indexed_result(document, chunks, vector_error=str(exc))
    except ModelGatewayCallError as exc:
        return knowledge_text_indexed_result(
            document,
            chunks,
            vector_error=exc.log.get("error") or "Model gateway embedding request failed",
        )
    return knowledge_vector_indexed_result(document, chunks, embeddings, embedding_context)
