from incident_types import ActionType, HelpfulAction, RequiredAction, ScenarioConfig, ServiceMetrics


def build_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        id="hard",
        name="Cascade Failure",
        difficulty="hard",
        alert="Sev-1: API error storm with cascading dependency failures.",
        services=["api", "db", "cache", "worker", "ingress"],
        max_steps=15,
        root_cause="cache outage caused db saturation and api failure",
        root_cause_aliases=[
            "cache outage cascade",
            "cache to db to api cascade",
            "cascade failure",
            "cache failure",
        ],
        initial_visible_services=["api", "ingress"],
        initial_visible_logs=[
            "api: ERROR upstream timeout querying cache",
            "ingress: WARN 502 spike routed to api",
        ],
        hidden_logs={
            "cache": [
                "cache: ERROR primary shard unavailable due to failed deploy hook",
                "cache: WARN reconnect storm from api clients",
            ],
            "db": [
                "db: ERROR connection pool saturation from cache misses",
                "db: WARN transaction queue backlog rising",
            ],
            "api": [
                "api: ERROR fallback path overload hitting db on every request",
                "api: WARN circuit breaker half-open flapping",
            ],
            "worker": [
                "worker: INFO no direct failures but retries increased",
                "worker: WARN noisy timeout unrelated to primary incident",
            ],
            "ingress": [
                "ingress: INFO traffic normal before cache failure window",
            ],
        },
        metrics={
            "api": ServiceMetrics(cpu_pct=88, memory_pct=90, error_rate=0.67, latency_ms=1800, rps=450),
            "db": ServiceMetrics(cpu_pct=93, memory_pct=79, error_rate=0.31, latency_ms=620, rps=700),
            "cache": ServiceMetrics(cpu_pct=12, memory_pct=35, error_rate=0.95, latency_ms=5, rps=40),
            "worker": ServiceMetrics(cpu_pct=44, memory_pct=51, error_rate=0.11, latency_ms=120, rps=210),
            "ingress": ServiceMetrics(cpu_pct=37, memory_pct=46, error_rate=0.35, latency_ms=70, rps=900),
        },
        required_actions=[
            RequiredAction(action=ActionType.RESTART_SERVICE, service="cache"),
            RequiredAction(action=ActionType.RESTART_SERVICE, service="db"),
            RequiredAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            RequiredAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        helpful_actions=[
            HelpfulAction(action=ActionType.CHECK_LOGS, service="cache"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="db"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="cache"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="db"),
            HelpfulAction(action=ActionType.RESTART_SERVICE, service="cache"),
            HelpfulAction(action=ActionType.RESTART_SERVICE, service="db"),
            HelpfulAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            HelpfulAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
    )
