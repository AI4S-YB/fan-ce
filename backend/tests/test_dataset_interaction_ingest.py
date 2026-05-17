from pathlib import Path
import sys

import h5py

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.datasets.services import dataset_domain_service


def create_cool_group(group, *, chrom_length, bin_size, pixels, weights=None):
    chroms_group = group.create_group("chroms")
    chroms_group.create_dataset("name", data=[b"chr1"])
    chroms_group.create_dataset("length", data=[chrom_length])

    nbins = chrom_length // bin_size
    bins_group = group.create_group("bins")
    bins_group.create_dataset("chrom", data=[0] * nbins, dtype="i8")
    bins_group.create_dataset("start", data=[index * bin_size for index in range(nbins)], dtype="i8")
    bins_group.create_dataset("end", data=[(index + 1) * bin_size for index in range(nbins)], dtype="i8")
    if weights is not None:
        bins_group.create_dataset("weight", data=weights, dtype="f8")

    sorted_pixels = sorted(pixels, key=lambda item: (item[0], item[1]))
    pixels_group = group.create_group("pixels")
    pixels_group.create_dataset("bin1_id", data=[item[0] for item in sorted_pixels], dtype="i8")
    pixels_group.create_dataset("bin2_id", data=[item[1] for item in sorted_pixels], dtype="i8")
    pixels_group.create_dataset("count", data=[item[2] for item in sorted_pixels], dtype="i8")

    row_offsets = []
    cursor = 0
    for bin_id in range(nbins):
        row_offsets.append(cursor)
        while cursor < len(sorted_pixels) and sorted_pixels[cursor][0] == bin_id:
            cursor += 1
    row_offsets.append(len(sorted_pixels))

    indexes_group = group.create_group("indexes")
    indexes_group.create_dataset("chrom_offset", data=[0, nbins], dtype="i8")
    indexes_group.create_dataset("bin1_offset", data=row_offsets, dtype="i8")

    group.attrs["bin-size"] = bin_size
    group.attrs["nbins"] = nbins
    group.attrs["nchroms"] = 1
    group.attrs["storage-mode"] = "symmetric-upper"


def create_cool_file(path, *, chrom_length, bin_size, pixels, weights=None):
    with h5py.File(path, "w") as handle:
        create_cool_group(
            handle,
            chrom_length=chrom_length,
            bin_size=bin_size,
            pixels=pixels,
            weights=weights,
        )


def create_mcool_file(path, *, resolutions):
    with h5py.File(path, "w") as handle:
        resolutions_group = handle.create_group("resolutions")
        for resolution, config in resolutions.items():
            create_cool_group(
                resolutions_group.create_group(str(resolution)),
                chrom_length=config["chrom_length"],
                bin_size=resolution,
                pixels=config["pixels"],
                weights=config.get("weights"),
            )


def test_validate_interaction_cool_reports_matrix_metadata(tmp_path):
    file_path = tmp_path / "matrix.cool"
    create_cool_file(
        file_path,
        chrom_length=30000,
        bin_size=10000,
        pixels=[(0, 0, 5), (0, 1, 7), (1, 1, 11)],
        weights=[1.0, 0.5, 1.5],
    )

    result = dataset_domain_service._validate_by_dataset_type(str(file_path), "interaction")

    assert result == {
        "format": "cool",
        "validated_path": str(file_path),
        "indexed": True,
        "bin_size": 10000,
        "balanced_supported": True,
        "shape": [3, 3],
        "resolution": 10000,
    }


def test_validate_interaction_mcool_detects_available_resolutions(tmp_path):
    file_path = tmp_path / "matrix.mcool"
    create_mcool_file(
        file_path,
        resolutions={
            10000: {"chrom_length": 20000, "pixels": [(0, 0, 1), (0, 1, 2), (1, 1, 3)], "weights": [1.0, 1.0]},
            50000: {"chrom_length": 50000, "pixels": [(0, 0, 9)], "weights": [1.0]},
        },
    )

    result = dataset_domain_service._validate_by_dataset_type(str(file_path), "interaction")

    assert result == {
        "format": "mcool",
        "validated_path": str(file_path),
        "indexed": True,
        "bin_size": 10000,
        "balanced_supported": True,
        "shape": [2, 2],
        "available_resolutions": [10000, 50000],
        "default_resolution": 10000,
    }


def test_index_interaction_cool_keeps_original_file(tmp_path):
    file_path = tmp_path / "matrix.cool"
    create_cool_file(
        file_path,
        chrom_length=20000,
        bin_size=10000,
        pixels=[(0, 0, 5), (0, 1, 7), (1, 1, 11)],
        weights=[1.0, 1.0],
    )

    result = dataset_domain_service._index_by_dataset_type(str(file_path), "interaction")

    assert result == {
        "indexed_path": str(file_path),
        "index_files": [],
        "operation": "cooler-ready",
        "bin_size": 10000,
        "balanced_supported": True,
        "resolution": 10000,
    }
