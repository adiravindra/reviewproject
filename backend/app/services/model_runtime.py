from contextlib import nullcontext
from dataclasses import dataclass
import os
from typing import Any


INFERENCE_DEVICE_ENV = "REVIEWINSIGHT_INFERENCE_DEVICE"
DEFAULT_INFERENCE_DEVICE = "auto"


@dataclass(frozen=True)
class InferenceDeviceSettings:
    model_device: str
    pipeline_device: int
    torch_dtype: Any | None = None


def resolve_inference_device(
    torch_module: Any | None = None,
    requested_device: str | None = None,
) -> InferenceDeviceSettings:
    requested = (requested_device or os.getenv(INFERENCE_DEVICE_ENV, DEFAULT_INFERENCE_DEVICE)).strip().casefold()
    torch_module = torch_module or _import_torch()

    if requested == "cpu":
        return InferenceDeviceSettings(model_device="cpu", pipeline_device=-1)

    cuda_available = bool(
        torch_module is not None
        and hasattr(torch_module, "cuda")
        and torch_module.cuda.is_available()
    )
    if requested.startswith("cuda") and cuda_available:
        index = _cuda_index(requested)
        return InferenceDeviceSettings(
            model_device=f"cuda:{index}",
            pipeline_device=index,
            torch_dtype=getattr(torch_module, "float16", None),
        )
    if requested == "auto" and cuda_available:
        return InferenceDeviceSettings(
            model_device="cuda:0",
            pipeline_device=0,
            torch_dtype=getattr(torch_module, "float16", None),
        )
    return InferenceDeviceSettings(model_device="cpu", pipeline_device=-1)


def inference_context() -> Any:
    torch_module = _import_torch()
    if torch_module is None or not hasattr(torch_module, "inference_mode"):
        return nullcontext()
    return torch_module.inference_mode()


def _import_torch() -> Any | None:
    try:
        import torch
    except Exception:
        return None
    return torch


def _cuda_index(requested_device: str) -> int:
    if ":" not in requested_device:
        return 0
    try:
        return max(0, int(requested_device.split(":", 1)[1]))
    except ValueError:
        return 0
