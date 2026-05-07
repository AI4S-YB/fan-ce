"""Analysis tool base classes — imported by plugin authors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileParam:
    """Declares an input file requirement."""
    name: str
    label: str
    accepted_asset_types: list     # e.g. ["variant_vcf", "functional_annotation"]
    accepted_formats: list         # e.g. ["vcf", "vcf.gz", "bcf"]
    accepted_dataset_types: list = field(default_factory=list)
    accepted_file_roles: list = field(default_factory=list)  # e.g. ["functional_annotation_table"]
    required: bool = True
    description: str = ""


@dataclass
class TextParam:
    name: str
    label: str
    default: str = ""
    description: str = ""


@dataclass
class ChoiceParam:
    name: str
    label: str
    choices: list
    default: str = ""
    description: str = ""


@dataclass
class IntParam:
    name: str
    label: str
    default: int = 0
    min: Optional[int] = None
    max: Optional[int] = None


@dataclass
class FloatParam:
    name: str
    label: str
    default: float = 0.0
    min: Optional[float] = None
    max: Optional[float] = None


@dataclass
class FileOutput:
    name: str
    label: str
    format: str
    description: str = ""


def _serialize_inputs(inputs: list) -> list:
    return [{"name": i.name, "label": i.label, "accepted_asset_types": i.accepted_asset_types,
             "accepted_formats": i.accepted_formats, "accepted_file_roles": i.accepted_file_roles,
             "required": i.required} for i in inputs]


def _serialize_params(params: list) -> list:
    result = []
    for p in params:
        d = {"name": p.name, "label": p.label, "type": type(p).__name__}
        if hasattr(p, "default"): d["default"] = p.default
        if hasattr(p, "choices"): d["choices"] = p.choices
        if hasattr(p, "min"): d["min"] = p.min
        if hasattr(p, "max"): d["max"] = p.max
        if hasattr(p, "description"): d["description"] = p.description
        result.append(d)
    return result


def _serialize_outputs(outputs: list) -> list:
    return [{"name": o.name, "label": o.label, "format": o.format} for o in outputs]


class BaseAnalysisTool(ABC):
    """Plugin authors subclass this and declare via entry_points."""

    # ── Must override ──
    tool_id: str = ""
    tool_version: str = "1.0.0"
    display_name: str = ""
    description: str = ""
    category: str = "utility"  # annotation | sequence | variant | expression | utility

    inputs: list = []
    parameters: list = []
    outputs: list = []

    timeout_seconds: int = 3600
    tool_status: str = "active"  # active | inactive | disabled
    dependencies: dict = field(default_factory=dict)  # {"pixi": [...], "conda": [...]}

    def get_input_schema(self) -> list:
        return _serialize_inputs(self.inputs)

    def get_parameter_schema(self) -> list:
        return _serialize_params(self.parameters)

    def get_output_schema(self) -> list:
        return _serialize_outputs(self.outputs)

    @abstractmethod
    def build_command(self, file_paths: dict, params: dict, work_dir: str) -> list:
        """Return the command to execute as a list of strings."""
        ...

    def validate_outputs(self, work_dir: str) -> list:
        """Check expected output files exist. Returns list of absolute paths."""
        import os
        paths = []
        for out in self.outputs:
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    if f.startswith(out.name) or f.endswith(f".{out.format}"):
                        paths.append(os.path.join(root, f))
        return paths
