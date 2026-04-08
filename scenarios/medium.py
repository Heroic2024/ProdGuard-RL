from incident_types import ActionType, HelpfulAction, RequiredAction, ScenarioConfig, ServiceMetrics


def build_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        id="medium",
        name="API Memory Leak",
        difficulty="medium",
        alert="High latency and intermittent 5xx in API after recent deploy. OOM kills observed.",
        services=["api", "db", "cache", "worker"],
        max_steps=12,
        root_cause="memory leak in api release",
        root_cause_aliases=[
            "api memory leak",
            "memory leak",
            "bad api deploy",
            "regression in api release",
        ],
        initial_visible_services=["api", "db"],
        initial_visible_logs=[
            "api: WARN pod restarted due to OOMKilled",
            "db: WARN occasional slow query but under SLO",
        ],
        hidden_logs={
            "api": [
                "api: ERROR heap usage grows 8% per minute",
                "api: WARN release v2026.04.07 introduced allocator regression",
            ],
            "db": [
                "db: ERROR temporary lock timeout from overloaded clients",
                "db: INFO primary healthy, replication delay 0ms",
            ],
            "cache": [
                "cache: INFO hit ratio stable at 0.93",
                "cache: WARN harmless eviction burst during traffic spike",
            ],
            "worker": [
                "worker: WARN queue lag increased then normalized",
            ],
        },
        metrics={
            "api": ServiceMetrics(cpu_pct=66, memory_pct=97, error_rate=0.41, latency_ms=980, rps=260),
            "db": ServiceMetrics(cpu_pct=39, memory_pct=63, error_rate=0.08, latency_ms=130, rps=340),
            "cache": ServiceMetrics(cpu_pct=28, memory_pct=48, error_rate=0.03, latency_ms=14, rps=520),
            "worker": ServiceMetrics(cpu_pct=54, memory_pct=57, error_rate=0.06, latency_ms=85, rps=180),
        },
        required_actions=[
            RequiredAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            RequiredAction(action=ActionType.SCALE_SERVICE, service="api"),
            RequiredAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        helpful_actions=[
            HelpfulAction(action=ActionType.CHECK_LOGS, service="api"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="api"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="db"),
            HelpfulAction(action=ActionType.SCALE_SERVICE, service="api"),
            HelpfulAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            HelpfulAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
    )
