import pytest

from app.services.assistant_chat_intents import (
    merge_assistant_references,
    plugin_connection_diagnostic_requested,
    scheduled_job_diagnostic_requested,
    scheduled_job_reference_needed_output,
    scheduled_job_run_once_requested,
    task_creation_guide_output,
    task_creation_guide_requested,
)


def test_assistant_chat_intents_detect_core_deterministic_commands():
    assert scheduled_job_run_once_requested("请帮我立即执行这个定时作业一次")
    assert not scheduled_job_run_once_requested("不要执行这个定时作业")
    assert scheduled_job_diagnostic_requested("为什么定时作业运行失败？")
    assert not scheduled_job_diagnostic_requested("帮我新增定时作业")
    assert plugin_connection_diagnostic_requested("插件连接失败，帮我排查原因")
    assert not plugin_connection_diagnostic_requested("帮我新增插件连接")
    assert task_creation_guide_requested("我要新增任务")
    assert not task_creation_guide_requested("帮我配置代码巡检定时作业")


@pytest.mark.parametrize(
    "message",
    [
        "@新建需求 新建一个需求任务，覆盖客服洞察转产品需求",
        "@新建 Bug 新建一个登录失败问题，关联任务 task_001",
        "@新建插件连接 帮我接入 GitHub",
        "@新建插件动作 新建一个写入飞书的任务动作",
        "@新建动作 新建一个写入飞书的任务动作",
        "@新建定时作业 每周从用户反馈中提取洞察",
        "@新建知识文档/导入任务 把客服 FAQ 导入知识库",
        (
            "@新建AI能力配置 新建一个基于用户客服聊天对话内容"
            "提炼成产品迭代需求的skill"
        ),
        "我要新建知识导入任务，请整理目录和权限",
        "我要新建需求任务，请生成需求草案",
    ],
)
def test_task_creation_guide_does_not_intercept_specific_create_flows(message):
    assert not task_creation_guide_requested(message)


def test_task_creation_guide_keeps_generic_create_entry_points():
    assert task_creation_guide_requested("我要新增任务")
    assert task_creation_guide_requested("我要新增 AI能力配置")


def test_assistant_chat_intent_outputs_keep_draft_first_guidance():
    selected_references = [
        {
            "id": "requirement_001",
            "title": "需求一",
            "type": "requirement",
            "url": "/delivery/requirements?requirement_id=requirement_001",
        }
    ]

    output = task_creation_guide_output(selected_references=selected_references)

    assert output["model"] == "assistant-deterministic"
    assert output["references"] == selected_references
    assert output["tool_results"][0]["tool"] == "assistant.task_creation_guide"
    assert output["tool_results"][0]["summary"]["draft_first"] is True
    assert "新增定时作业" in output["suggestions"]
    assert "新增动作" in output["suggestions"]
    assert "新增插件动作" not in output["suggestions"]


def test_assistant_chat_intent_outputs_prompt_for_unique_scheduled_job_reference():
    output = scheduled_job_reference_needed_output(
        attempted_queries=["每周反馈"],
        selected_references=[],
    )

    assert output["model"] == "assistant-deterministic"
    assert "没有找到唯一匹配的定时作业" in output["answer"]
    assert output["tool_results"][0]["summary"] == {
        "queries": ["每周反馈"],
        "status": "needs_scheduled_job_reference",
    }


def test_merge_assistant_references_deduplicates_and_limits_valid_links():
    references = [
        {"id": str(index), "title": f"对象 {index}", "type": "requirement", "url": "/x"}
        for index in range(8)
    ]
    merged = merge_assistant_references(
        references[:4],
        [
            references[1],
            {"id": "bad", "title": "缺 URL", "type": "requirement"},
            *references[4:],
        ],
    )

    assert [item["id"] for item in merged] == ["0", "1", "2", "3", "4", "5"]
