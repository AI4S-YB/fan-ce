from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

try:
    import h5py
    import numpy as np
except ImportError:  # pragma: no cover - exercised via runtime environment
    h5py = None
    np = None


def _require_hdf5_runtime():
    if h5py is None or np is None:
        raise HTTPException(status_code=503, detail="h5py and numpy are required for cool/mcool querying")


def _decode_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "decode"):
        return value.decode("utf-8")
    return str(value)


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field_name}: {value}") from exc


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _require_group(group: Any, group_path: str):
    if not isinstance(group, h5py.Group):
        raise HTTPException(status_code=400, detail=f"invalid cool/mcool structure: missing group {group_path}")
    return group


def _require_dataset(group: h5py.Group, dataset_name: str):
    if dataset_name not in group:
        raise HTTPException(status_code=400, detail=f"invalid cool/mcool structure: missing dataset {group.name}/{dataset_name}")
    return group[dataset_name]


def _read_chroms(group: h5py.Group) -> List[Dict[str, Any]]:
    chroms_group = _require_group(group.get("chroms"), f"{group.name}/chroms")
    chrom_names = [_decode_value(item) for item in _require_dataset(chroms_group, "name")[()]]
    chrom_lengths = [int(item) for item in _require_dataset(chroms_group, "length")[()]]
    if len(chrom_names) != len(chrom_lengths):
        raise HTTPException(status_code=400, detail="invalid cool/mcool structure: chrom name/length length mismatch")
    return [{"name": name, "length": length} for name, length in zip(chrom_names, chrom_lengths)]


def _read_bin_size(group: h5py.Group, selected_resolution: Optional[int]) -> int:
    bin_size = group.attrs.get("bin-size")
    if bin_size is not None:
        return int(bin_size)
    bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
    starts = _require_dataset(bins_group, "start")
    ends = _require_dataset(bins_group, "end")
    if len(starts) > 0:
        return int(ends[0]) - int(starts[0])
    if selected_resolution:
        return int(selected_resolution)
    return 0


def _read_nbins(group: h5py.Group) -> int:
    if group.attrs.get("nbins") is not None:
        return int(group.attrs["nbins"])
    bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
    return int(len(_require_dataset(bins_group, "start")))


def _read_storage_mode(group: h5py.Group) -> str:
    raw_value = group.attrs.get("storage-mode")
    if raw_value is None:
        return "symmetric-upper"
    return _decode_value(raw_value)


def _resolve_matrix_group(file_path: str, requested_resolution: Any = None) -> Tuple[str, Any, h5py.Group, List[int], Optional[int]]:
    _require_hdf5_runtime()
    handle = h5py.File(file_path, "r")
    resolutions_group = handle.get("resolutions")
    if isinstance(resolutions_group, h5py.Group):
        resolutions: List[int] = []
        for key in resolutions_group.keys():
            try:
                resolutions.append(int(str(key)))
            except ValueError:
                continue
        if not resolutions:
            handle.close()
            raise HTTPException(status_code=400, detail="mcool file does not expose any numeric resolutions")
        resolutions = sorted(set(resolutions))
        selected_resolution = resolutions[0] if requested_resolution in {None, ""} else _to_int(requested_resolution, "resolution")
        group = resolutions_group.get(str(selected_resolution))
        if not isinstance(group, h5py.Group):
            handle.close()
            raise HTTPException(status_code=400, detail=f"resolution {selected_resolution} is not available in mcool file")
        return "mcool", handle, group, resolutions, selected_resolution
    return "cool", handle, handle, [], None


def _load_group_context(file_path: str, requested_resolution: Any = None) -> Dict[str, Any]:
    file_format, handle, group, resolutions, selected_resolution = _resolve_matrix_group(
        file_path=file_path,
        requested_resolution=requested_resolution,
    )
    try:
        chroms = _read_chroms(group)
        bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
        pixels_group = _require_group(group.get("pixels"), f"{group.name}/pixels")
        _require_dataset(bins_group, "chrom")
        _require_dataset(bins_group, "start")
        _require_dataset(bins_group, "end")
        _require_dataset(pixels_group, "bin1_id")
        _require_dataset(pixels_group, "bin2_id")
        _require_dataset(pixels_group, "count")
        return {
            "file_format": file_format,
            "group": group,
            "chroms": chroms,
            "available_resolutions": resolutions,
            "selected_resolution": selected_resolution,
            "bin_size": _read_bin_size(group, selected_resolution),
            "nbins": _read_nbins(group),
            "balanced_supported": "weight" in bins_group,
            "storage_mode": _read_storage_mode(group),
        }
    finally:
        handle.close()


def inspect_interaction_matrix(file_path: str, requested_resolution: Any = None) -> Dict[str, Any]:
    context = _load_group_context(file_path=file_path, requested_resolution=requested_resolution)
    data = {
        "source": "cool",
        "format": context["file_format"],
        "bin_size": int(context["bin_size"]),
        "chroms": context["chroms"],
        "shape": [int(context["nbins"]), int(context["nbins"])],
        "balanced_supported": bool(context["balanced_supported"]),
    }
    if context["file_format"] == "mcool":
        data["available_resolutions"] = context["available_resolutions"]
        data["default_resolution"] = context["available_resolutions"][0]
        data["resolution"] = int(context["selected_resolution"])
    else:
        data["resolution"] = int(context["bin_size"])
    return data


def list_interaction_resolutions(file_path: str) -> Dict[str, Any]:
    context = _load_group_context(file_path=file_path)
    if context["file_format"] != "mcool":
        raise HTTPException(status_code=400, detail="resolutions_list is supported for mcool files only")
    return {
        "source": "cool",
        "format": "mcool",
        "resolutions": context["available_resolutions"],
        "default_resolution": context["available_resolutions"][0],
        "count": len(context["available_resolutions"]),
    }


def _get_chrom_bin_bounds(group: h5py.Group, chroms: List[Dict[str, Any]], chrom_name: str) -> Tuple[int, int]:
    chrom_names = [item["name"] for item in chroms]
    if chrom_name not in chrom_names:
        raise HTTPException(status_code=404, detail=f"chromosome not found in cool/mcool file: {chrom_name}")
    chrom_index = chrom_names.index(chrom_name)

    indexes_group = group.get("indexes")
    if isinstance(indexes_group, h5py.Group) and "chrom_offset" in indexes_group:
        offsets = np.asarray(indexes_group["chrom_offset"][()], dtype=np.int64)
        nbins = _read_nbins(group)
        start_offset = int(offsets[chrom_index])
        if chrom_index + 1 < len(offsets):
            end_offset = int(offsets[chrom_index + 1])
        else:
            end_offset = nbins
        return start_offset, end_offset

    bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
    chrom_values = np.asarray(_require_dataset(bins_group, "chrom")[()])
    if np.issubdtype(chrom_values.dtype, np.number):
        matches = np.where(chrom_values.astype(np.int64) == chrom_index)[0]
    else:
        normalized = np.asarray([_decode_value(item) for item in chrom_values], dtype=object)
        matches = np.where(normalized == chrom_name)[0]
    if matches.size == 0:
        return 0, 0
    return int(matches[0]), int(matches[-1]) + 1


def _select_region_bins(group: h5py.Group, chroms: List[Dict[str, Any]], chrom_name: str, start: int, end: int) -> Tuple[List[int], List[str]]:
    chrom_start, chrom_end = _get_chrom_bin_bounds(group, chroms, chrom_name)
    if chrom_end <= chrom_start:
        return [], []

    bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
    starts = np.asarray(_require_dataset(bins_group, "start")[chrom_start:chrom_end], dtype=np.int64)
    ends = np.asarray(_require_dataset(bins_group, "end")[chrom_start:chrom_end], dtype=np.int64)
    overlap = np.where((starts < end) & (ends > start))[0]
    if overlap.size == 0:
        return [], []
    global_ids = (overlap + chrom_start).astype(np.int64)
    labels = [f"{chrom_name}:{int(starts[idx])}-{int(ends[idx])}" for idx in overlap.tolist()]
    return global_ids.tolist(), labels


def _row_pixel_bounds(offsets: Optional[np.ndarray], row_bin: int, pixel_count: int) -> Tuple[int, int]:
    if offsets is None:
        return 0, pixel_count
    if row_bin >= len(offsets):
        return 0, 0
    start = int(offsets[row_bin])
    end = int(offsets[row_bin + 1]) if row_bin + 1 < len(offsets) else pixel_count
    return start, end


def _normalize_count_value(raw_count: Any, balanced: bool, weights: Optional[np.ndarray], bin1_id: int, bin2_id: int):
    if not balanced:
        return int(raw_count) if isinstance(raw_count, (int, np.integer)) else float(raw_count)
    if weights is None:
        raise HTTPException(status_code=400, detail="balanced matrix access requires bins/weight in cool/mcool file")
    weight1 = float(weights[bin1_id])
    weight2 = float(weights[bin2_id])
    if not np.isfinite(weight1) or not np.isfinite(weight2):
        return None
    return float(raw_count) * weight1 * weight2


def query_interaction_matrix_slice(file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    requested_resolution = params.get("resolution")
    file_format, handle, group, available_resolutions, selected_resolution = _resolve_matrix_group(
        file_path=file_path,
        requested_resolution=requested_resolution,
    )
    try:
        chroms = _read_chroms(group)
        source_chrom = params.get("chrom") or params.get("seq_id")
        source_start = params.get("start")
        source_end = params.get("end")
        if not source_chrom or source_start is None or source_end is None:
            raise HTTPException(status_code=400, detail="chrom/seq_id, start and end are required")

        region_start = _to_int(source_start, "start")
        region_end = _to_int(source_end, "end")
        if region_start < 0 or region_end <= region_start:
            raise HTTPException(status_code=400, detail="invalid region: require 0 <= start < end")

        target_chrom = str(params.get("target_chrom") or source_chrom)
        target_start = region_start if params.get("target_start") is None else _to_int(params.get("target_start"), "target_start")
        target_end = region_end if params.get("target_end") is None else _to_int(params.get("target_end"), "target_end")
        if target_start < 0 or target_end <= target_start:
            raise HTTPException(status_code=400, detail="invalid target region: require 0 <= target_start < target_end")

        balanced = _to_bool(params.get("balanced"), default=False)
        limit_bins = _to_int(params.get("limit_bins") or 200, "limit_bins")
        if limit_bins <= 0:
            raise HTTPException(status_code=400, detail="limit_bins must be a positive integer")

        source_bin_ids, x_labels = _select_region_bins(group, chroms, str(source_chrom), region_start, region_end)
        target_bin_ids, y_labels = _select_region_bins(group, chroms, target_chrom, target_start, target_end)
        if len(source_bin_ids) > limit_bins or len(target_bin_ids) > limit_bins:
            raise HTTPException(
                status_code=400,
                detail=f"requested region expands to too many bins ({len(source_bin_ids)} x {len(target_bin_ids)}), limit_bins={limit_bins}",
            )

        bins_group = _require_group(group.get("bins"), f"{group.name}/bins")
        weights = None
        if balanced:
            if "weight" not in bins_group:
                raise HTTPException(status_code=400, detail="balanced matrix access is not available for this cool/mcool file")
            weights = np.asarray(bins_group["weight"][()], dtype=float)

        matrix_dtype = float if balanced else np.int64
        matrix = np.zeros((len(source_bin_ids), len(target_bin_ids)), dtype=matrix_dtype)
        source_index = {int(bin_id): idx for idx, bin_id in enumerate(source_bin_ids)}
        target_index = {int(bin_id): idx for idx, bin_id in enumerate(target_bin_ids)}

        pixels_group = _require_group(group.get("pixels"), f"{group.name}/pixels")
        bin1_dataset = _require_dataset(pixels_group, "bin1_id")
        bin2_dataset = _require_dataset(pixels_group, "bin2_id")
        count_dataset = _require_dataset(pixels_group, "count")
        pixel_count = len(count_dataset)

        indexes_group = group.get("indexes")
        offsets = None
        if isinstance(indexes_group, h5py.Group) and "bin1_offset" in indexes_group:
            offsets = np.asarray(indexes_group["bin1_offset"][()], dtype=np.int64)

        storage_mode = _read_storage_mode(group)
        row_bins = sorted(set(source_bin_ids) | set(target_bin_ids)) if storage_mode == "symmetric-upper" else source_bin_ids

        for row_bin in row_bins:
            start_offset, end_offset = _row_pixel_bounds(offsets, int(row_bin), pixel_count)
            if end_offset <= start_offset:
                continue
            bin1_values = np.asarray(bin1_dataset[start_offset:end_offset], dtype=np.int64)
            bin2_values = np.asarray(bin2_dataset[start_offset:end_offset], dtype=np.int64)
            raw_counts = count_dataset[start_offset:end_offset]

            for bin1_id, bin2_id, raw_count in zip(bin1_values.tolist(), bin2_values.tolist(), raw_counts.tolist()):
                value = _normalize_count_value(raw_count, balanced=balanced, weights=weights, bin1_id=bin1_id, bin2_id=bin2_id)
                if value is None:
                    continue

                source_pos = source_index.get(int(bin1_id))
                target_pos = target_index.get(int(bin2_id))
                if source_pos is not None and target_pos is not None:
                    matrix[source_pos, target_pos] = value

                if storage_mode == "symmetric-upper":
                    source_pos = source_index.get(int(bin2_id))
                    target_pos = target_index.get(int(bin1_id))
                    if source_pos is not None and target_pos is not None:
                        matrix[source_pos, target_pos] = value

        bin_size = _read_bin_size(group, selected_resolution)
        return {
            "source": "cool",
            "format": file_format,
            "resolution": int(selected_resolution) if selected_resolution is not None else int(bin_size),
            "region": f"{source_chrom}:{region_start}-{region_end}",
            "target_region": f"{target_chrom}:{target_start}-{target_end}",
            "bin_size": int(bin_size),
            "x_labels": x_labels,
            "y_labels": y_labels,
            "matrix": matrix.tolist(),
            "shape": [len(source_bin_ids), len(target_bin_ids)],
            "balanced": balanced,
            "available_resolutions": available_resolutions if file_format == "mcool" else [],
        }
    finally:
        handle.close()
