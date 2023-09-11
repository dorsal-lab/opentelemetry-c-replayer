from os import environ
from typing import Optional, Sequence

from grpc import ChannelCredentials, Compression
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin, _get_credentials, environ_to_compression)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import \
    ExportLogsServiceRequest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import \
    LogsServiceStub
from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs
from opentelemetry.sdk._logs._internal.export import LogExporter, \
    LogExportResult
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION, OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS, OTEL_EXPORTER_OTLP_LOGS_INSECURE,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT)


# pylint: disable=no-member
class OTLPLogExporter(
    LogExporter,
    OTLPExporterMixin[
        ResourceLogs, ExportLogsServiceRequest, LogExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP log export
    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: gRPC compression method to use
    """

    _result = LogExportResult
    _stub = LogsServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):

        if insecure is None:
            insecure_environ = environ.get(OTEL_EXPORTER_OTLP_LOGS_INSECURE)
            if insecure_environ is not None:
                insecure = insecure_environ.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE
            )

        if timeout is None:
            environ_timeout = environ.get(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT)
            timeout = (
                int(environ_timeout) if environ_timeout is not None else None
            )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_LOGS_COMPRESSION)
            if compression is None
            else compression
        )

        super().__init__(
            **{
                "endpoint": endpoint
                            or environ.get(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT),
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                           or environ.get(OTEL_EXPORTER_OTLP_LOGS_HEADERS),
                "timeout": timeout,
                "compression": compression,
            }
        )

    def _translate_data(
        self, data: Sequence[ResourceLogs]
    ) -> ExportLogsServiceRequest:
        return ExportLogsServiceRequest(
            resource_logs=data
        )

    def export(self, logs: Sequence[ResourceLogs]) -> LogExportResult:
        return self._export(logs)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    @property
    def _exporting(self):
        return "logs"

    def shutdown(self):
        pass
