from incident_types import (
    ActionType,
    HelpfulAction,
    RequiredAction,
    ScenarioConfig,
    ServiceMetrics,
)


def get_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        id="easy_db_outage",
        name="Database Primary Outage",
        difficulty="easy",
        alert="P1: Checkout API 5xx burn-rate alert triggered in prod-us-east-1 after routine maintenance window.",
        services=["api", "db", "worker"],
        max_steps=8,
        root_cause="database primary unavailable",
        root_cause_aliases=[
            "db primary down",
            "database outage",
            "database unavailable",
            "postgres primary unavailable",
        ],
        initial_visible_services=["api", "worker"],
        initial_visible_logs=[
            "api: ERROR request_id=9f2a1 route=/checkout dependency timeout while creating order",
            "api: WARN retry_policy exhausted for transactional storage dependency",
            "worker: WARN publish latency elevated to 220ms but job ack rate stable",
        ],
        hidden_logs={
            "api": [
                "api: ERROR sqlstate=08006 connection failure while acquiring db session",
                "api: WARN fallback read path healthy; write path blocked on primary database",
            ],
            "db": [
                "db: ERROR could not accept connections: startup in progress after checkpoint replay",
                "db: FATAL terminating connection due to administrator command",
                "db: LOG database system is ready to accept connections",
            ],
            "worker": [
                "worker: INFO background reconciliation completed with no data drift",
                "worker: WARN write jobs blocked waiting for transactional store",
            ],
        },
        metrics={
            "api": ServiceMetrics(
                cpu_pct=44.0,
                memory_pct=62.0,
                latency_ms=1450.0,
                error_rate=0.69,
                rps=180.0,
            ),
            "db": ServiceMetrics(
                cpu_pct=5.0,
                memory_pct=30.0,
                latency_ms=0.0,
                error_rate=1.0,
                rps=0.0,
            ),
            "worker": ServiceMetrics(
                cpu_pct=24.0,
                memory_pct=41.0,
                latency_ms=92.0,
                error_rate=0.05,
                rps=55.0,
            ),
        },
        required_actions=[
            RequiredAction(action=ActionType.CHECK_METRICS, service="db"),
            RequiredAction(action=ActionType.CHECK_LOGS, service="db"),
            RequiredAction(action=ActionType.RESTART_SERVICE, service="db"),
            RequiredAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        helpful_actions=[
            HelpfulAction(action=ActionType.CHECK_METRICS, service="db"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="api"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="db"),
            HelpfulAction(action=ActionType.RESTART_SERVICE, service="db"),
            HelpfulAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        resolution_bonus=11.5,
        wrong_diagnosis_penalty=5.0,
    )
