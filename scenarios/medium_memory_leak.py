from incident_types import (
    ActionType,
    HelpfulAction,
    RequiredAction,
    ScenarioConfig,
    ServiceMetrics,
)


def get_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        id="medium_memory_leak",
        name="API Memory Leak After Release",
        difficulty="medium",
        alert="P1: Checkout tail latency and 5xx breached SLO following canary-to-full rollout in prod-us-east-1.",
        services=["api", "db", "cache", "worker"],
        max_steps=12,
        root_cause="memory leak in api release",
        root_cause_aliases=[
            "api memory leak",
            "memory leak",
            "allocator regression in api",
            "bad api rollout",
        ],
        initial_visible_services=["api", "db"],
        initial_visible_logs=[
            "api: WARN pod restart detected, reason=OOMKilled",
            "api: ERROR timeout serving /checkout while waiting on downstream dependencies",
            "db: WARN lock wait timeout observed on order_ledger hot partition",
            "cache: WARN transient eviction burst reported by edge telemetry",
        ],
        hidden_logs={
            "api": [
                "api: ERROR heap growth anomaly: resident set +6%/min over last 10 min",
                "api: WARN build=v2026.04.08 introduced request context retention in middleware",
                "api: ERROR allocator pressure: goroutine-like context map never released on failed requests",
                "api: INFO rollback candidate available for previous stable build",
            ],
            "db": [
                "db: INFO replication healthy; no failover events in incident window",
                "db: WARN connection churn increased from api restarts",
                "db: INFO lock graph indicates secondary contention, not primary failure source",
            ],
            "cache": [
                "cache: WARN eviction spike during traffic burst (within normal recovery envelope)",
                "cache: INFO hit ratio stable at 0.91",
                "cache: INFO no node failover, shard ownership stable",
            ],
            "worker": [
                "worker: WARN queue lag briefly elevated due to API write retries",
                "worker: INFO queue drain recovered without intervention",
            ],
        },
        metrics={
            "api": ServiceMetrics(
                cpu_pct=69.0,
                memory_pct=98.0,
                latency_ms=1180.0,
                error_rate=0.43,
                rps=265.0,
            ),
            "db": ServiceMetrics(
                cpu_pct=41.0,
                memory_pct=66.0,
                latency_ms=145.0,
                error_rate=0.11,
                rps=360.0,
            ),
            "cache": ServiceMetrics(
                cpu_pct=34.0,
                memory_pct=51.0,
                latency_ms=18.0,
                error_rate=0.04,
                rps=540.0,
            ),
            "worker": ServiceMetrics(
                cpu_pct=52.0,
                memory_pct=58.0,
                latency_ms=90.0,
                error_rate=0.07,
                rps=175.0,
            ),
        },
        required_actions=[
            RequiredAction(action=ActionType.CHECK_METRICS, service="db"),
            RequiredAction(action=ActionType.CHECK_LOGS, service="db"),
            RequiredAction(action=ActionType.CHECK_METRICS, service="api"),
            RequiredAction(action=ActionType.CHECK_LOGS, service="api"),
            RequiredAction(action=ActionType.SCALE_SERVICE, service="api"),
            RequiredAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            RequiredAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        helpful_actions=[
            HelpfulAction(action=ActionType.CHECK_METRICS, service="api"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="db"),
            HelpfulAction(action=ActionType.CHECK_METRICS, service="cache"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="api"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="db"),
            HelpfulAction(action=ActionType.CHECK_LOGS, service="cache"),
            HelpfulAction(action=ActionType.SCALE_SERVICE, service="api"),
            HelpfulAction(action=ActionType.ROLLBACK_DEPLOYMENT),
            HelpfulAction(action=ActionType.DECLARE_ROOT_CAUSE),
        ],
        resolution_bonus=13.0,
        wrong_diagnosis_penalty=6.0,
    )
