ALTER TABLE integration_plugins
    DROP CONSTRAINT IF EXISTS ck_integration_plugins_protocol;

ALTER TABLE integration_plugins
    ADD CONSTRAINT ck_integration_plugins_protocol
    CHECK (
        protocol IN (
            'http',
            'internal_read_model',
            'mcp_http',
            'mcp_stdio',
            'runner_polling',
            'runner_websocket'
        )
    );

ALTER TABLE plugin_actions
    DROP CONSTRAINT IF EXISTS ck_plugin_actions_action_type;

ALTER TABLE plugin_actions
    ADD CONSTRAINT ck_plugin_actions_action_type
    CHECK (action_type IN ('http_request', 'internal_query', 'mcp_tool'));
