import time
from contextlib import contextmanager

from opentelemetry import trace

from .config import settings

tracer = trace.get_tracer("iea_mcp")


def setup() -> None:
    """Send traces to Application Insights if a connection string is set."""
    if settings.applicationinsights_connection_string:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=settings.applicationinsights_connection_string)


@contextmanager
def span(tool: str, user, **filters):
    start = time.perf_counter()
    with tracer.start_as_current_span(tool) as s:
        s.set_attribute("iea.tool", tool)
        s.set_attribute("iea.user", user.hashed_id)
        for key, value in filters.items():
            if value is not None:
                s.set_attribute(f"iea.filter.{key}", str(value))
        try:
            yield s
        except Exception as e:
            s.set_attribute("iea.error", type(e).__name__)
            raise
        finally:
            s.set_attribute("iea.latency_ms", round((time.perf_counter() - start) * 1000))