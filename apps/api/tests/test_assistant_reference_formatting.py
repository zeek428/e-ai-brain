from types import SimpleNamespace

from app.services.assistant_reference_formatting import (
    assistant_reference_for_entity,
    assistant_reference_matches_query,
    assistant_reference_type_preferences,
    execution_trace_href,
    merge_reference_lists,
    merge_reference_lists_by_type,
    reference_permission_label,
)


def test_assistant_reference_formatting_builds_execution_trace_links_and_titles():
    store = SimpleNamespace(
        scheduled_jobs={
            "scheduled_job_feedback": {"name": "每周用户反馈洞察抽取"},
        },
    )

    reference = assistant_reference_for_entity(
        "scheduled_job_run",
        {
            "id": "scheduled_job_run_001",
            "scheduled_job_id": "scheduled_job_feedback",
            "status": "failed",
        },
        current_store=store,
    )

    assert reference == {
        "id": "scheduled_job_run_001",
        "title": "每周用户反馈洞察抽取 / failed",
        "type": "scheduled_job_run",
        "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_001",
    }
    assert execution_trace_href("run 001", "scheduled_job_run") == (
        "/governance/execution-traces?source_id=run+001&source_type=scheduled_job_run"
    )


def test_assistant_reference_formatting_matches_scheduled_job_semantic_query():
    assert assistant_reference_matches_query(
        "scheduled_job",
        {"id": "job_001", "name": "每周用户反馈洞察抽取", "summary": "提取有价值反馈"},
        "每周反馈提取",
        current_store=None,
    )
    assert not assistant_reference_matches_query(
        "scheduled_job",
        {"id": "job_002", "name": "线上日志异常分析"},
        "每周反馈提取",
        current_store=None,
    )


def test_assistant_reference_formatting_merges_and_balances_reference_types():
    references = [
        {"id": "bug_001", "title": "Bug", "type": "bug", "url": "/bug"},
        {
            "id": "requirement_001",
            "title": "需求",
            "type": "requirement",
            "url": "/requirement",
        },
        {
            "id": "knowledge_001",
            "title": "知识",
            "type": "knowledge_document",
            "url": "/knowledge",
        },
    ]

    assert merge_reference_lists(
        references[:2],
        [
            references[0],
            {"id": "bad", "title": "缺 URL", "type": "bug"},
            references[2],
        ],
        limit=3,
    ) == references
    assert [item["type"] for item in merge_reference_lists_by_type(references, limit=3)] == [
        "knowledge_document",
        "requirement",
        "bug",
    ]


def test_assistant_reference_formatting_preferences_and_permission_labels():
    preferences = assistant_reference_type_preferences("定时作业运行失败，帮我排查")

    assert preferences["scheduled_job_run"] < preferences["scheduled_job"]
    assert reference_permission_label(
        {"roles": [], "permissions": ["diagnostics.execution_traces.read"]},
        "assistant_chat_run",
    ) == "执行诊断权限可引用"
    assert reference_permission_label(
        {"roles": [], "permissions": ["system.plugins.manage"]},
        "plugin_connection",
    ) == "插件管理权限可引用"
    assert reference_permission_label({"roles": [], "permissions": []}, "requirement") == "可引用"
