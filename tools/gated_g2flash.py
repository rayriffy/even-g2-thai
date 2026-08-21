#!/usr/bin/env python3
"""Fail-closed launcher for the reviewed g2flash transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

G2FLASH_COMMIT = "877c8d9490db0d3717ca012dd0f54556af3701bd"
VALUE_OPTIONS = {
    "-c",
    "--connection",
    "-f",
    "--firmware",
    "--lens",
    "--stop-before",
}
FLAG_OPTIONS: set[str] = set()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise ValueError(process.stderr.strip() or "unable to inspect g2flash checkout")
    return process.stdout.strip()


def option_values(arguments: list[str], names: set[str]) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in names and index + 1 < len(arguments):
            values.append(arguments[index + 1])
            index += 2
            continue
        if argument in names:
            raise ValueError(f"{argument} requires a value")
        for name in names:
            if name.startswith("--") and argument.startswith(f"{name}="):
                values.append(argument.split("=", 1)[1])
                break
        index += 1
    return values


def firmware_argument(arguments: list[str]) -> Path:
    values = option_values(arguments, {"-f", "--firmware"})
    if len(values) != 1 or not values[0]:
        raise ValueError("g2flash arguments must include exactly one firmware image")
    return Path(values[0]).expanduser().resolve()


def validate_allowed_arguments(arguments: list[str]) -> None:
    seen: set[str] = set()
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        name = argument.split("=", 1)[0]
        if name in VALUE_OPTIONS:
            if name in seen:
                raise ValueError(f"duplicate G2Flash option {name} is not permitted")
            seen.add(name)
            if "=" not in argument:
                if index + 1 >= len(arguments):
                    raise ValueError(f"{name} requires a value")
                index += 2
                continue
        elif name in FLAG_OPTIONS:
            if name in seen or "=" in argument:
                raise ValueError(f"invalid or duplicate G2Flash flag {name}")
            seen.add(name)
        else:
            raise ValueError(f"unreviewed or abbreviated G2Flash option {argument}")
        index += 1


def validate_operation(arguments: list[str], operation: str) -> None:
    validate_allowed_arguments(arguments)
    if operation == "discover":
        if arguments:
            raise ValueError("discover takes no G2Flash forwarding arguments")
        return
    if "--recompute-checksums" in arguments:
        raise ValueError("checksum mutation is not permitted through the BLE launcher")
    connections = option_values(arguments, {"-c", "--connection"})
    lenses = option_values(arguments, {"--lens"})
    stops = option_values(arguments, {"--stop-before"})
    if len(connections) != 1 or not connections[0]:
        raise ValueError("exactly one connection string is required")
    connection = urlparse(connections[0])
    if (
        connection.scheme != "g2"
        or connection.netloc != "local"
        or connection.path not in {"", "/"}
        or connection.params
        or connection.fragment
    ):
        raise ValueError("only the reviewed g2://local transport is permitted")
    query = parse_qs(connection.query, keep_blank_values=True)
    if set(query) - {"left", "right", "addressType"}:
        raise ValueError("g2://local connection contains unreviewed parameters")
    for side in ("left", "right"):
        if len(query.get(side, [])) != 1 or not query[side][0]:
            raise ValueError(f"g2://local requires exactly one {side} identifier")
    address_types = query.get("addressType", [])
    if len(address_types) > 1 or (address_types and address_types[0] not in {"public", "random"}):
        raise ValueError("g2://local addressType must be public or random")
    if len(lenses) != 1 or lenses[0] not in {"left", "right", "both"}:
        raise ValueError("exactly one valid --lens value is required")
    if operation == "transport":
        if lenses[0] != "both" or stops != ["file_check"]:
            raise ValueError("transport operation requires --lens both --stop-before file_check")
    elif operation in {"flash", "rollback"}:
        if lenses[0] == "both" or stops:
            raise ValueError(f"{operation} requires one lens and no --stop-before override")
    else:
        raise ValueError(f"unsupported operation {operation}")


def observed_value(value: object) -> str:
    if value is None:
        return "<missing>"
    if value == "":
        return "<empty>"
    if isinstance(value, (str, int, bool)):
        return str(value)
    raise ValueError("selection record contains a non-scalar compatibility field")


def validate_selection_record(
    path: Path,
    target_version: str,
    compatibility: dict[str, object],
    artifact: dict[str, object],
) -> None:
    protected = json.loads(path.read_text())
    if not isinstance(protected, dict):
        raise ValueError("protected selection record must be a JSON object")
    if protected.get("schema_version") != 1:
        raise ValueError("protected selection record has an unsupported schema")
    if protected.get("target_version") != target_version:
        raise ValueError("protected selection record targets another firmware version")
    if "hardware_revision" not in protected:
        raise ValueError("protected selection record is missing hardware_revision")
    protected_hardware = observed_value(protected["hardware_revision"])
    redacted_hardware = observed_value(compatibility["hardware_revision"])
    if protected_hardware in {"<empty>", "<missing>"} or redacted_hardware in {"<empty>", "<missing>"}:
        raise ValueError("hardware revision evidence must not be empty")
    if protected_hardware != redacted_hardware:
        raise ValueError("protected hardware revision does not match redacted evidence")
    if protected.get("source") != compatibility["source"]:
        raise ValueError("protected selection source does not match redacted evidence")
    ota_info = protected.get("device_ota_info")
    if not isinstance(ota_info, dict):
        raise ValueError("protected selection record is missing device_ota_info")
    if observed_value(ota_info.get("version")) != target_version:
        raise ValueError("protected DeviceOtaInfo version does not match target")
    if not str(ota_info.get("sn", "")).strip():
        raise ValueError("protected DeviceOtaInfo is missing the owned device serial")
    endpoints = protected.get("endpoints")
    if not isinstance(endpoints, dict):
        raise ValueError("protected selection record is missing endpoints")
    for side in ("left", "right"):
        name = endpoints.get(f"{side}_name")
        expected_hash = compatibility.get(f"{side}_endpoint_name_sha256")
        version = endpoints.get(f"{side}_version")
        if not isinstance(name, str) or not name or not isinstance(version, str) or version != target_version:
            raise ValueError(f"protected {side} endpoint evidence is incomplete")
        if not isinstance(expected_hash, str) or hashlib.sha256(name.encode()).hexdigest() != expected_hash:
            raise ValueError(f"protected {side} endpoint name does not match redacted evidence")
    for key in ("mode", "region", "type"):
        if key not in ota_info:
            raise ValueError(f"protected DeviceOtaInfo is missing {key}")
        if observed_value(ota_info[key]) != observed_value(compatibility[key]):
            raise ValueError(f"protected DeviceOtaInfo {key} does not match redacted evidence")
    if ota_info.get("subPath") != artifact["sub_path"]:
        raise ValueError("protected DeviceOtaInfo subPath does not match locked artifact")
    if ota_info.get("fileSize") != artifact["file_size"]:
        raise ValueError("protected DeviceOtaInfo fileSize does not match locked artifact")
    if ota_info.get("fileSign") != artifact["file_sign"]:
        raise ValueError("protected DeviceOtaInfo fileSign does not match locked artifact")
    if protected.get("cdn_base", "") + ota_info["subPath"] != artifact["source_url"]:
        raise ValueError("protected CDN base and subPath do not match locked artifact URL")


def verify_ble_endpoints(interpreter: Path, arguments: list[str], selection_record: Path) -> None:
    connection = option_values(arguments, {"-c", "--connection"})[0]
    query = parse_qs(urlparse(connection).query)
    protected = json.loads(selection_record.read_text())
    endpoints = protected["endpoints"]
    environment = {
        "LEFT_UUID": query["left"][0],
        "RIGHT_UUID": query["right"][0],
        "LEFT_NAME": endpoints["left_name"],
        "RIGHT_NAME": endpoints["right_name"],
    }
    code = (
        "import asyncio, os, sys\n"
        "from bleak import BleakScanner\n"
        "async def verify():\n"
        "    devices = await BleakScanner.discover(timeout=20, return_adv=True)\n"
        "    for side in ('LEFT', 'RIGHT'):\n"
        "        uuid = os.environ[side + '_UUID']\n"
        "        expected = os.environ[side + '_NAME']\n"
        "        if uuid not in devices: return 2\n"
        "        device, advertisement = devices[uuid]\n"
        "        actual = advertisement.local_name or device.name or ''\n"
        "        if actual != expected: return 3\n"
        "    return 0\n"
        "raise SystemExit(asyncio.run(verify()))\n"
    )
    process = subprocess.run([str(interpreter), "-c", code], env={**os.environ, **environment})
    if process.returncode:
        raise ValueError("BLE endpoints do not match protected authenticated device evidence")


def check_ready(
    project_root: Path,
    g2flash_root: Path,
    arguments: list[str],
    operation: str,
    selection_record: Optional[Path] = None,
) -> Path:
    patch_spec_path = project_root / "patches/thai_patches.json"
    patch_spec = json.loads(patch_spec_path.read_text())
    base_match = re.fullmatch(r"g2_(.+)\.bin", patch_spec["base"])
    if not base_match:
        raise ValueError("patch specification has an invalid base filename")
    target_version = base_match.group(1)

    record_path = project_root / f"docs/rebases/{target_version}.json"
    if not record_path.is_file():
        raise ValueError(f"missing compatibility record {record_path}")
    record = json.loads(record_path.read_text())
    if record.get("target_version") != target_version:
        raise ValueError("compatibility record target does not match patch specification")
    if record.get("stock_sha256") != patch_spec["base_sha256"]:
        raise ValueError("compatibility record stock hash does not match patch specification")
    if record.get("patched_sha256") != patch_spec["output_sha256"]:
        raise ValueError("compatibility record patched hash does not match patch specification")
    if record.get("component_count") != patch_spec["metadata"]["component_count"]:
        raise ValueError("compatibility record component count does not match patch specification")
    artifact = record.get("selected_artifact", {})

    compatibility = record.get("compatibility", {})
    status = compatibility.get("status", "missing")
    if status != "verified":
        raise ValueError(f"hardware compatibility status is {status}; BLE contact is blocked")
    required = (
        "hardware_revision",
        "mode",
        "region",
        "type",
        "selection_record_sha256",
        "source",
        "verified_at",
        "left_endpoint_name_sha256",
        "right_endpoint_name_sha256",
    )
    missing = [key for key in required if compatibility.get(key) is None]
    if missing or compatibility.get("serial_redacted") is not True:
        raise ValueError(f"compatibility evidence is incomplete: {missing}")
    artifact_fields = ("source_url", "sub_path", "file_size", "file_sign")
    missing_artifact = [key for key in artifact_fields if artifact.get(key) is None]
    if missing_artifact:
        raise ValueError(f"selected artifact evidence is incomplete: {missing_artifact}")
    if artifact["file_size"] != record.get("stock_size"):
        raise ValueError("selected artifact size does not match locked stock metadata")
    if artifact["source_url"] != record.get("stock_url"):
        raise ValueError("selected artifact URL does not match locked stock metadata")
    selection_hash = compatibility["selection_record_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", selection_hash):
        raise ValueError("selection_record_sha256 must identify the protected full record")
    if selection_record is None or not selection_record.is_file():
        raise ValueError("protected DeviceOtaInfo selection record is required")
    if sha256_file(selection_record) != selection_hash:
        raise ValueError("protected DeviceOtaInfo record hash does not match redacted evidence")
    for key in ("hardware_revision", "mode", "region", "type", "source", "verified_at"):
        if not str(compatibility[key]).strip():
            raise ValueError(f"compatibility evidence field {key} is empty")
    if any(compatibility[key] == "<missing>" for key in ("mode", "region", "type")):
        raise ValueError("compatibility variant fields must be observed")
    validate_selection_record(selection_record, target_version, compatibility, artifact)
    validate_operation(arguments, operation)

    if operation == "discover":
        firmware = None
    else:
        firmware = firmware_argument(arguments)
        if not firmware.is_file():
            raise ValueError(f"firmware image does not exist: {firmware}")
        firmware_hash = sha256_file(firmware)
        expected_hash = (
            patch_spec["base_sha256"] if operation == "rollback" else patch_spec["output_sha256"]
        )
        if firmware_hash != expected_hash:
            raise ValueError(f"{operation} operation received the wrong firmware artifact")

    if git_output(g2flash_root, "rev-parse", "HEAD") != G2FLASH_COMMIT:
        raise ValueError(f"g2flash must be pinned to {G2FLASH_COMMIT}")
    status_lines = git_output(
        g2flash_root, "status", "--porcelain", "--untracked-files=all"
    ).splitlines()
    if any(line != "?? .DS_Store" for line in status_lines):
        raise ValueError("g2flash has local source changes; use a fresh clean checkout")

    interpreter = g2flash_root / "venv/bin/python"
    script = g2flash_root / "g2flash.py"
    if not interpreter.is_file() or not script.is_file():
        raise ValueError("pinned g2flash virtualenv or script is missing")
    return interpreter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g2flash-root", type=Path, default=Path(__file__).parents[2] / "g2flash")
    parser.add_argument("--selection-record", type=Path)
    parser.add_argument("--operation", choices=("discover", "transport", "flash", "rollback"), required=True)
    parser.add_argument("g2flash_args", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    forwarded = args.g2flash_args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    project_root = Path(__file__).resolve().parents[1]
    g2flash_root = args.g2flash_root.expanduser().resolve()
    try:
        selection_record = args.selection_record.expanduser().resolve() if args.selection_record else None
        interpreter = check_ready(
            project_root,
            g2flash_root,
            forwarded,
            args.operation,
            selection_record,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"flash preflight blocked: {error}", file=sys.stderr)
        return 2
    if args.operation == "discover":
        protected = json.loads(selection_record.read_text())
        endpoints = protected["endpoints"]
        environment = {
            "LEFT_NAME": endpoints["left_name"],
            "RIGHT_NAME": endpoints["right_name"],
        }
        discovery = (
            "import asyncio\n"
            "from bleak import BleakScanner\n"
            "async def scan():\n"
            "    devices = await BleakScanner.discover(timeout=20, return_adv=True)\n"
            "    for address, (device, advertisement) in devices.items():\n"
            "        name = advertisement.local_name or device.name or ''\n"
            "        if name == __import__('os').environ['LEFT_NAME']: print('left', address)\n"
            "        if name == __import__('os').environ['RIGHT_NAME']: print('right', address)\n"
            "asyncio.run(scan())\n"
        )
        process = subprocess.run(
            [str(interpreter), "-c", discovery],
            check=False,
            env={**os.environ, **environment},
        )
    else:
        try:
            verify_ble_endpoints(interpreter, forwarded, selection_record)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            print(f"flash preflight blocked: {error}", file=sys.stderr)
            return 2
        process = subprocess.run(
            [str(interpreter), str(g2flash_root / "g2flash.py"), *forwarded],
            check=False,
        )
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
