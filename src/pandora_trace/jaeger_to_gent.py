import json
import os
from pathlib import Path
from typing import Optional, List

import requests

JAEGER_URL = "http://localhost:16686"
APP = "hotelReservation"


def download_traces_from_jaeger(service_name: str, jaeger_url: str, target_dir: Path) -> int:
    response = requests.get(f"{jaeger_url}/api/traces?service={service_name}&limit=10000").json()
    traces = []
    for trace in response["data"]:
        trace_id = trace["traceID"]
        response = requests.get(f"{jaeger_url}/api/traces/{trace_id}").json()
        traces.extend(response["data"])
    os.makedirs(target_dir, exist_ok=True)
    target_file = target_dir / f"{service_name}.json"
    with open(target_file, "w") as f:
        json.dump(traces, f, indent=4)
    # print(f"Downloaded {len(traces)} traces for {service_name} to {target_file}.")
    return len(traces)


def download_traces_from_jaeger_for_all_services(target_dir: Path, jaeger_url: str = JAEGER_URL) -> int:
    response = requests.get(f"{jaeger_url}/api/services")
    total = 0
    all_services = response.json()["data"] or []
    for service in all_services:
        if "jaeger" in service:
            # print("Skipping jaeger service", service)
            continue
        total += download_traces_from_jaeger(service, jaeger_url, target_dir)
    return total


def _handle_jaeger_trace(jaeger_trace: dict) -> dict:
    from gent.ml.app_denormalizer import Component, prepare_tx_structure

    def get_service_name(s):
        for tag in s["tags"]:
            if tag["key"] == "http.url":
                hostname = tag["value"].split('?')[0]
                if hostname.startswith("http://"):
                    hostname = hostname[len("http://"):]
                return hostname
        return jaeger_trace["processes"][s["processID"]]["serviceName"]
    span_to_service_name = {s["spanID"]: (get_service_name(s), s["startTime"]) for s in jaeger_trace["spans"]}
    span_id_to_ts_name = {}
    components = []
    for span in jaeger_trace["spans"]:
        service_name, start_time = span_to_service_name[span["spanID"]]
        dup_names = [t for s, t in span_to_service_name.values() if s == service_name]
        dup_names = sorted(dup_names)
        name = f'{service_name}*{dup_names.index(start_time)}'
        span_id_to_ts_name[span["spanID"]] = name
    for span in jaeger_trace["spans"]:
        components.append(Component(
            component_id=span_id_to_ts_name[span["spanID"]],
            start_time=span["startTime"],
            end_time=span["startTime"] + span["duration"],
            has_error=any(
                ((tag["key"] == "error" and tag["value"] is True)
                or tag["key"] == "http.status_code" and tag["value"] > 300)
                for tag in span["tags"]),
            children_ids=[span_id_to_ts_name.get(ref["spanID"]) for ref in span["references"] if ref["refType"] == "CHILD_OF"],
            group="",
            metadata={t["key"]: t["value"] for t in span["tags"]} | {f"process_{t['key']}": t["value"] for t in jaeger_trace['processes'][span["processID"]]['tags']},
            component_type="jaeger",
            duration=span["duration"]
        ))
    return prepare_tx_structure(transaction_id=jaeger_trace["traceID"], components=components)


def translate_jaeger_to_gent(from_dir: str, to_dir: Optional[str] = None) -> None:
    if not to_dir:
        to_dir = from_dir.replace("raw_jaeger", "gent")
    os.makedirs(to_dir, exist_ok=True)
    for service_file in os.listdir(from_dir):
        with open(os.path.join(from_dir, service_file)) as f:
            jaeger_traces = json.load(f)
        translate_jaeger_to_gent_from_list(jaeger_traces, os.path.join(to_dir, service_file))


def translate_jaeger_to_gent_from_list(jaeger_traces: List[dict], filepath: Optional[str] = None) -> None:
        with open(filepath, "w") as f:
            for jaeger_trace in jaeger_traces:
                gent_trace = _handle_jaeger_trace(jaeger_trace)
                if gent_trace:
                    f.write(json.dumps(gent_trace) + ",\n")


if __name__ == '__main__':
    download_traces_from_jaeger_for_all_services(target_dir=f"data/{APP}/raw_jaeger/")
    translate_jaeger_to_gent(from_dir=f"data/{APP}/raw_jaeger/", to_dir=f"data/{APP}/gent/")

