from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def require_str(obj: Dict[str, Any], key: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val:
        raise ValueError(f"欄位 {key} 必須是非空字串")
    return val


def require_int(obj: Dict[str, Any], key: str) -> int:
    val = obj.get(key)
    if not isinstance(val, int):
        raise ValueError(f"欄位 {key} 必須是整數")
    return val


def optional_int(obj: Dict[str, Any], key: str) -> Optional[int]:
    val = obj.get(key)
    if val is None:
        return None
    if not isinstance(val, int):
        raise ValueError(f"欄位 {key} 必須是整數")
    return val


def require_float(obj: Dict[str, Any], key: str) -> float:
    val = obj.get(key)
    if not isinstance(val, (int, float)):
        raise ValueError(f"欄位 {key} 必須是數字")
    return float(val)


@dataclass(frozen=True)
class StartMessage:
    session_id: str
    audio_format: str
    sample_rate: int
    channels: int

    @staticmethod
    def parse(obj: Dict[str, Any]) -> "StartMessage":
        return StartMessage(
            session_id=require_str(obj, "session_id"),
            audio_format=require_str(obj, "audio_format"),
            sample_rate=require_int(obj, "sample_rate"),
            channels=require_int(obj, "channels"),
        )


@dataclass(frozen=True)
class TextDeltaMessage:
    session_id: str
    seq: int
    text: str

    @staticmethod
    def parse(obj: Dict[str, Any]) -> "TextDeltaMessage":
        return TextDeltaMessage(
            session_id=require_str(obj, "session_id"),
            seq=require_int(obj, "seq"),
            text=require_str(obj, "text"),
        )


@dataclass(frozen=True)
class TextEndMessage:
    session_id: str
    seq: int

    @staticmethod
    def parse(obj: Dict[str, Any]) -> "TextEndMessage":
        return TextEndMessage(
            session_id=require_str(obj, "session_id"),
            seq=require_int(obj, "seq"),
        )


@dataclass(frozen=True)
class CancelMessage:
    session_id: str
    seq: int

    @staticmethod
    def parse(obj: Dict[str, Any]) -> "CancelMessage":
        return CancelMessage(
            session_id=require_str(obj, "session_id"),
            seq=require_int(obj, "seq"),
        )


@dataclass(frozen=True)
class ResumeMessage:
    session_id: str
    last_unit_index_received: int

    @staticmethod
    def parse(obj: Dict[str, Any]) -> "ResumeMessage":
        return ResumeMessage(
            session_id=require_str(obj, "session_id"),
            last_unit_index_received=require_int(obj, "last_unit_index_received"),
        )

