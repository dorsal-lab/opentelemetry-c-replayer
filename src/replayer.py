"""
replayer.py

Read all opentelemetry-c CTF traces and send them to an
Opentelemetry collector using OpenTelelemetry Protocol for GRPC.
"""
import logging
from argparse import ArgumentParser
from pathlib import Path

import bt2
from google.protobuf.message import DecodeError
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans
from opentelemetry.sdk.trace.export import SpanExportResult
from otlp_span_exporter import OTLPSpanExporter
from tqdm.auto import tqdm


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="""
            Read all opentelemetry-c CTF traces and send them to an Opentelemetry collector
            using OpenTelelemetry Protocol for GRPC.
        """,
        epilog="""
            Instead, you can also configure the collector GRPC server using the following environment variables :
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE, OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, OTEL_EXPORTER_OTLP_TRACES_HEADERS,
            OTEL_EXPORTER_OTLP_TRACES_INSECURE, OTEL_EXPORTER_OTLP_TRACES_TIMEOUT.
            Description of all those environment variables are available here :
            https://opentelemetry.io/docs/reference/specification/protocol/exporter/#configuration-options
        """
    )
    parser.add_argument('-i', '--ctf-traces-folder-path',
                        action='store',
                        help='The path of folder where ctf traces',
                        required=True,
                        type=str,
                        dest='input_folder')
    parser.add_argument('-e', '--otel-exporter-otlp-traces-endpoint',
                        action='store',
                        help='The OTel collector GRPC server endpoint. If set, we assume the endpoint is insecure',
                        required=False,
                        type=str,
                        dest='otel_exporter_otlp_traces_endpoint')
    return parser


if __name__ == "__main__":

    logging.root.setLevel(logging.INFO)

    args = get_parser().parse_args()

    if not Path(args.input_folder).exists():
        logging.fatal(
            "The path of the CTF traces must be passed as first argument of the script.")
        exit(1)

    # Create the span exporter
    span_exporter = OTLPSpanExporter(
        endpoint=args.otel_exporter_otlp_traces_endpoint,
        insecure=True if args.otel_exporter_otlp_traces_endpoint else None
    )

    n_tel_data = 0
    n_tel_data_exported = 0

    # Iterate over trace messages
    logging.info("Exporting telemetry data ...")
    n_events_messages = sum(1 for _ in bt2.TraceCollectionMessageIterator(args.input_folder))
    for msg in tqdm(bt2.TraceCollectionMessageIterator(args.input_folder), total=n_events_messages):
        # pylint: disable=protected-access
        if not isinstance(msg, bt2._EventMessageConst):
            continue
        # An event message holds a trace event.
        event = msg.event

        if event.name.startswith("opentelemetry:"):
            n_tel_data += 1

        if event.name == "opentelemetry:resource_spans":
            # Export resource spans
            resource_spans_bytes = bytes(list(event['resource_spans']))

            # resource_spans_str_as_bytes = resource_spans_str.encode()
            # print(type(resource_spans_str_as_bytes))
            resource_spans = ResourceSpans()
            try:
                resource_spans.ParseFromString(resource_spans_bytes)
            except DecodeError:
                logging.error("Unable to parse one %s event", event.name)
                continue

            # TODO (augustinsangam): In future export spans in group
            # Exporting spans one by one
            result = span_exporter.export([resource_spans])
            if (result == SpanExportResult.FAILURE):
                logging.error(
                    "Unable to export trace id %s",
                    resource_spans.scope_spans[0].spans[0].trace_id)
            else:
                n_tel_data_exported += 1
        elif event.name == "opentelemetry:resource_logs":
            # TODO (augustinsangam): Add supports for logs
            pass
        elif event.name == "opentelemetry:resource_metrics":
            # TODO (augustinsangam): Add supports for metrics
            pass

    logging.info("Exporting done. %d/%d telemetry data exported.",
                 n_tel_data_exported, n_tel_data)
