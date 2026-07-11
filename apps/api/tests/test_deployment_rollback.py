from app.services.deployment_rollback import auto_rollback_allowed


def test_auto_rollback_obeys_risk_threshold() -> None:
    config = {"auto_on_failure": True, "auto_risk_threshold": "medium"}

    assert auto_rollback_allowed(risk_level="low", rollback_config=config) is True
    assert auto_rollback_allowed(risk_level="medium", rollback_config=config) is True
    assert auto_rollback_allowed(risk_level="high", rollback_config=config) is False
    assert auto_rollback_allowed(risk_level="critical", rollback_config=config) is False


def test_auto_rollback_must_be_explicitly_enabled() -> None:
    assert auto_rollback_allowed(risk_level="low", rollback_config={}) is False
