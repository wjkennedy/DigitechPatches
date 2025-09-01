#!/usr/bin/env python3
"""Utilities for managing GNX3000 .g3kp preset files.

This module provides a small command line interface for working with
GNX3000 preset files. Presets are stored in an XML based format with the
``.g3kp`` extension. The tool can list preset names, update preset names
and modify parameter values across many files which makes it convenient for
bulk management tasks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Namespace used by the GNX3k preset XML files
NS = {"p": "http://www.digitech.com/xml/preset"}
ET.register_namespace("", NS["p"])

# Manufacturer ID used for GNX3000 SysEx messages (Harman/DigiTech)
DIGITECH_ID = [0x00, 0x01, 0x0f]


class GNX3kPreset:
    """Representation of a single GNX3000 preset."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()

    # ------------------------------------------------------------------
    @property
    def name(self) -> str | None:
        """Return the preset name."""
        name_elem = self.root.find("p:Name", NS)
        return name_elem.text if name_elem is not None else None

    @name.setter
    def name(self, value: str) -> None:
        name_elem = self.root.find("p:Name", NS)
        if name_elem is None:
            name_elem = ET.SubElement(self.root, f"{{{NS['p']}}}Name")
        name_elem.text = value

    # ------------------------------------------------------------------
    def get_param(self, param_id: int) -> str | None:
        """Return the value for the parameter with ``param_id``.

        Parameters are identified by their numeric ``ID`` field. ``None`` is
        returned if the parameter cannot be located.
        """
        for param in self.root.findall("p:Params/p:Param", NS):
            id_elem = param.find("p:ID", NS)
            if id_elem is not None and id_elem.text == str(param_id):
                value_elem = param.find("p:Value", NS)
                return value_elem.text if value_elem is not None else None
        return None

    # ------------------------------------------------------------------
    def set_param(self, param_id: int, value: str) -> bool:
        """Set ``param_id`` to ``value``.

        Returns ``True`` if the parameter was found and updated.
        """
        for param in self.root.findall("p:Params/p:Param", NS):
            id_elem = param.find("p:ID", NS)
            if id_elem is not None and id_elem.text == str(param_id):
                value_elem = param.find("p:Value", NS)
                if value_elem is None:
                    value_elem = ET.SubElement(param, f"{{{NS['p']}}}Value")
                value_elem.text = str(value)
                return True
        return False

    # ------------------------------------------------------------------
    def save(self, path: Path | str | None = None) -> None:
        """Write the preset back to disk."""
        target = Path(path) if path is not None else self.path
        self.tree.write(target, encoding="UTF-8", xml_declaration=True)


# ----------------------------------------------------------------------
def resolve_files(patterns: list[str]) -> list[Path]:
    """Expand filename patterns into a sorted list of Paths."""
    files: list[Path] = []
    for pat in patterns:
        matched = sorted(Path().glob(pat))
        if matched:
            files.extend(matched)
        else:
            files.append(Path(pat))
    return files


# ----------------------------------------------------------------------
def cmd_list(args: argparse.Namespace) -> None:
    for path in resolve_files(args.files):
        preset = GNX3kPreset(path)
        print(f"{path}: {preset.name}")


def cmd_set_name(args: argparse.Namespace) -> None:
    for path in resolve_files(args.files):
        preset = GNX3kPreset(path)
        preset.name = args.name
        preset.save()
        print(f"updated {path}")


def cmd_get_param(args: argparse.Namespace) -> None:
    for path in resolve_files(args.files):
        preset = GNX3kPreset(path)
        value = preset.get_param(args.id)
        print(f"{path}: {value}")


def cmd_set_param(args: argparse.Namespace) -> None:
    for path in resolve_files(args.files):
        preset = GNX3kPreset(path)
        if preset.set_param(args.id, args.value):
            preset.save()
            print(f"updated {path}")
        else:
            print(f"{path}: parameter {args.id} not found", file=sys.stderr)


def _preset_sysex_chunks(path: Path, chunk_size: int = 256) -> list[list[int]]:
    """Return SysEx data chunks for the preset at ``path``."""
    data = Path(path).read_bytes()
    chunks: list[list[int]] = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i : i + chunk_size]
        # Ensure bytes are 7-bit clean for MIDI SysEx transport
        chunks.append(DIGITECH_ID + [b & 0x7F for b in chunk])
    return chunks


def cmd_upload(args: argparse.Namespace) -> None:
    files = resolve_files(args.files)
    messages: list[list[int]] = []
    for path in files:
        messages.extend(_preset_sysex_chunks(path))
    if args.dry_run:
        for msg in messages:
            hex_bytes = " ".join(f"{b:02X}" for b in [0xF0] + msg + [0xF7])
            print(hex_bytes)
        return
    try:
        import mido
    except ImportError:  # pragma: no cover - optional dependency
        print("mido library required for upload", file=sys.stderr)
        return
    with mido.open_output(args.port) as out:
        for msg in messages:
            out.send(mido.Message("sysex", data=msg))
    print(f"sent {len(messages)} sysex messages to {args.port}")


# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="list preset names")
    p_list.add_argument("files", nargs="*", default=["*.g3kp"], help="files or patterns")
    p_list.set_defaults(func=cmd_list)

    p_set_name = sub.add_parser("set-name", help="set the preset name")
    p_set_name.add_argument("name", help="new preset name")
    p_set_name.add_argument("files", nargs="*", default=["*.g3kp"], help="files or patterns")
    p_set_name.set_defaults(func=cmd_set_name)

    p_get_param = sub.add_parser("get-param", help="get parameter value by ID")
    p_get_param.add_argument("id", type=int, help="parameter ID")
    p_get_param.add_argument("files", nargs="*", default=["*.g3kp"], help="files or patterns")
    p_get_param.set_defaults(func=cmd_get_param)

    p_set_param = sub.add_parser("set-param", help="set parameter value by ID")
    p_set_param.add_argument("id", type=int, help="parameter ID")
    p_set_param.add_argument("value", help="new value")
    p_set_param.add_argument("files", nargs="*", default=["*.g3kp"], help="files or patterns")
    p_set_param.set_defaults(func=cmd_set_param)

    p_upload = sub.add_parser("upload", help="send presets to a GNX3000 over MIDI")
    p_upload.add_argument("port", help="MIDI output port name")
    p_upload.add_argument("files", nargs="+", help="preset files or patterns")
    p_upload.add_argument("--dry-run", action="store_true", help="print SysEx bytes instead of sending")
    p_upload.set_defaults(func=cmd_upload)

    return parser


# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
