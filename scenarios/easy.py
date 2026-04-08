from incident_types import ActionType, HelpfulAction, RequiredAction, ScenarioConfig, ServiceMetrics


def build_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        id="easy",
        name="Database Down",
        difficulty="easy",
        alert="Critical: API availability dropped. Initial probe indicates database connection refused.",
        services=["api", "db", "worker"],
        max_steps=10,
        root_cause="database down",
        root_cause_aliases=["db down", "database outage", "database unavailable"],
        initial_visible_services=["api"],
        initial_visible_logs=["api: ERROR failed to connect to db: connection refused"],
        hidden_logs={
            "db": [
                "db: FATAL postmaster exited unexpectedly",
                "db: INFO service unhealthy but restartable",
            ],
            "api": [
                "api: WARN retry loop exhausted for db client",
            ],
            "worker": [
                "worker: INFO idle, queue depth normal",
            ],
        },
        metrics={
            "api": ServiceMetrics(cpu_pct=42, memory_pct=58, error_rate=0.72, latency_ms=1500, rps=120),
            "db": ServiceMetrics(cpu_pct=4, memory_pct=22, error_rate=1.0, latency_ms=0, rps=0),
            "worker": ServiceMetrics(cpu_pct=18, memory_pct=35, error_rate=0.02, latency_ms=45, rps=40),
        },
        required_actions=[
            RequiredAction(action=ActionType.RESTART_SERVICE, service="db"),
            RequiredAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        helpful_actions=[
            HelpfulAction(action=ActionType.CHECK_LOGS, service="db"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="db"),
            HelpfulAction(action=ActionType.RESTART_SERVICE, service="db"),
            HelpfulAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
    )
