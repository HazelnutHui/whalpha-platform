"""Pure outcome-blind numerical kernel for factor-space diagnostics."""

from __future__ import annotations

from itertools import combinations

import numpy as np
from numpy.typing import NDArray

from tip_api.contracts.analytics.v1.quant_research_factor_space_diagnostic import (
    FactorSpaceClusterMergeV1,
    FactorSpaceComponentV1,
    FactorSpaceDimensionV1,
    FactorSpaceInputV1,
    FactorSpaceLoadingV1,
    FactorSpacePairV1,
    FactorSpacePanelKind,
    FactorSpacePanelReportV1,
    FactorSpaceScaleV1,
    FactorSpaceVifStatus,
    FactorSpaceVifV1,
    FactorSpaceSourceBindingV1,
    QuantResearchFactorSpaceDiagnosticV1,
    factor_space_diagnostic_fingerprint,
)


FloatArray = NDArray[np.float64]


class FactorSpaceDiagnosticError(ValueError):
    """Raised when the zero-outcome diagnostic input is not admissible."""


def build_factor_space_diagnostic_report(
    *,
    source_bindings: tuple[FactorSpaceSourceBindingV1, ...],
    security_panel: FactorSpacePanelReportV1,
    market_state_panel: FactorSpacePanelReportV1,
) -> QuantResearchFactorSpaceDiagnosticV1:
    payload = {
        "source_bindings": source_bindings,
        "panels": (security_panel, market_state_panel),
    }
    provisional = QuantResearchFactorSpaceDiagnosticV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorSpaceDiagnosticV1.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_space_diagnostic_fingerprint(provisional),
        }
    )


def build_factor_space_panel(
    *,
    panel: FactorSpacePanelKind,
    input_ids: tuple[str, ...],
    economic_families: tuple[str, ...],
    values: FloatArray,
    group_keys: tuple[str, ...] | None = None,
) -> FactorSpacePanelReportV1:
    _validate_input(input_ids, economic_families, values, group_keys, panel)
    if panel is FactorSpacePanelKind.SECURITY_CROSS_SECTION:
        assert group_keys is not None
        transformed, scales = _cross_section_transform(values, input_ids, group_keys)
    else:
        transformed, scales = _market_state_transform(values, input_ids)

    complete_mask = np.all(np.isfinite(transformed), axis=1)
    complete = transformed[complete_mask]
    if complete.shape[0] <= len(input_ids):
        raise FactorSpaceDiagnosticError("complete-case support is insufficient")
    complete = _column_standardize(complete)
    correlation = np.corrcoef(complete, rowvar=False)
    if correlation.shape != (len(input_ids), len(input_ids)) or not np.all(
        np.isfinite(correlation)
    ):
        raise FactorSpaceDiagnosticError("complete-case correlation differs")

    pairs = _pairs(values, transformed, input_ids)
    merges = _cluster_merges(correlation, input_ids)
    rank = int(np.linalg.matrix_rank(correlation))
    if rank == len(input_ids):
        inverse = np.linalg.inv(correlation)
        vifs = tuple(
            FactorSpaceVifV1(
                input_id=input_id,
                status=FactorSpaceVifStatus.AVAILABLE,
                value=_decimal(inverse[index, index]),
            )
            for index, input_id in enumerate(input_ids)
        )
        condition_status = "available"
        condition_number = _decimal(np.linalg.cond(correlation))
    else:
        vifs = tuple(
            FactorSpaceVifV1(
                input_id=input_id,
                status=FactorSpaceVifStatus.SINGULAR,
            )
            for input_id in input_ids
        )
        condition_status = "singular"
        condition_number = None

    components, dimension = _pca(
        complete,
        input_ids,
        rank=rank,
        condition_status=condition_status,
        condition_number=condition_number,
    )
    return FactorSpacePanelReportV1(
        panel=panel,
        inputs=tuple(
            FactorSpaceInputV1(input_id=input_id, economic_family=family)
            for input_id, family in zip(input_ids, economic_families, strict=True)
        ),
        row_count=values.shape[0],
        complete_case_count=int(complete_mask.sum()),
        complete_case_share=_decimal(float(complete_mask.mean())),
        scales=scales,
        pairs=pairs,
        cluster_merges=merges,
        vifs=vifs,
        components=components,
        dimension=dimension,
    )


def _validate_input(input_ids, economic_families, values, group_keys, panel) -> None:
    if (
        len(input_ids) < 2
        or len(input_ids) != len(economic_families)
        or len(set(input_ids)) != len(input_ids)
        or values.ndim != 2
        or values.shape[1] != len(input_ids)
        or values.shape[0] < 3
        or np.any(np.isinf(values))
    ):
        raise FactorSpaceDiagnosticError("factor-space input shape differs")
    if panel is FactorSpacePanelKind.SECURITY_CROSS_SECTION:
        if group_keys is None or len(group_keys) != values.shape[0]:
            raise FactorSpaceDiagnosticError("cross-section groups differ")
    elif group_keys is not None:
        raise FactorSpaceDiagnosticError("market-state panel cannot carry row groups")


def _cross_section_transform(values, input_ids, group_keys):
    transformed = np.full_like(values, np.nan, dtype=np.float64)
    groups: dict[str, list[int]] = {}
    for index, key in enumerate(group_keys):
        groups.setdefault(key, []).append(index)
    for column in range(values.shape[1]):
        for indices in groups.values():
            positions = np.asarray(indices, dtype=np.int64)
            current = values[positions, column]
            available = np.isfinite(current)
            count = int(available.sum())
            if count < 2:
                continue
            ranked = _average_ranks(current[available])
            centered = 2.0 * (((ranked - 0.5) / count) - 0.5)
            transformed[positions[available], column] = centered
    scales = []
    for column, input_id in enumerate(input_ids):
        available = transformed[np.isfinite(transformed[:, column]), column]
        if available.size < 2:
            raise FactorSpaceDiagnosticError(f"{input_id} has insufficient scale support")
        location = float(available.mean())
        scale = float(available.std(ddof=1))
        if not np.isfinite(scale) or scale <= 0.0:
            raise FactorSpaceDiagnosticError(f"{input_id} has zero scale")
        transformed[np.isfinite(transformed[:, column]), column] = (
            available - location
        ) / scale
        scales.append(
            FactorSpaceScaleV1(
                input_id=input_id,
                method="same_session_midrank_then_development_scale",
                available_count=int(available.size),
                location=_decimal(location),
                scale=_decimal(scale),
            )
        )
    return transformed, tuple(scales)


def _market_state_transform(values, input_ids):
    transformed = np.full_like(values, np.nan, dtype=np.float64)
    scales = []
    for column, input_id in enumerate(input_ids):
        available_mask = np.isfinite(values[:, column])
        available = values[available_mask, column]
        if available.size < 3:
            raise FactorSpaceDiagnosticError(f"{input_id} has insufficient scale support")
        location = float(np.median(available))
        scale = float(1.4826 * np.median(np.abs(available - location)))
        method = "development_median_mad"
        if not np.isfinite(scale) or scale <= 0.0:
            scale = float(available.std(ddof=1))
            method = "development_median_std_fallback"
        if not np.isfinite(scale) or scale <= 0.0:
            raise FactorSpaceDiagnosticError(f"{input_id} has zero scale")
        transformed[available_mask, column] = (available - location) / scale
        scales.append(
            FactorSpaceScaleV1(
                input_id=input_id,
                method=method,
                available_count=int(available.size),
                location=_decimal(location),
                scale=_decimal(scale),
            )
        )
    return transformed, tuple(scales)


def _column_standardize(values: FloatArray) -> FloatArray:
    centered = values - values.mean(axis=0)
    scale = centered.std(axis=0, ddof=1)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0.0):
        raise FactorSpaceDiagnosticError("complete-case matrix has zero scale")
    return centered / scale


def _pairs(raw, transformed, input_ids):
    output = []
    for left, right in combinations(range(len(input_ids)), 2):
        shared = np.isfinite(raw[:, left]) & np.isfinite(raw[:, right])
        shared_transformed = np.isfinite(transformed[:, left]) & np.isfinite(
            transformed[:, right]
        )
        if int(shared.sum()) < 3 or int(shared_transformed.sum()) < 3:
            raise FactorSpaceDiagnosticError("pair support is insufficient")
        raw_left = raw[shared, left]
        raw_right = raw[shared, right]
        rank_dependence = np.corrcoef(
            _average_ranks(raw_left), _average_ranks(raw_right)
        )[0, 1]
        pearson = np.corrcoef(
            transformed[shared_transformed, left],
            transformed[shared_transformed, right],
        )[0, 1]
        if not np.isfinite(rank_dependence) or not np.isfinite(pearson):
            raise FactorSpaceDiagnosticError("pair dependence is non-finite")
        output.append(
            FactorSpacePairV1(
                left_input_id=input_ids[left],
                right_input_id=input_ids[right],
                shared_count=int(shared.sum()),
                both_missing_count=int(
                    ((~np.isfinite(raw[:, left])) & (~np.isfinite(raw[:, right]))).sum()
                ),
                pearson=_decimal(pearson),
                rank_dependence=_decimal(rank_dependence),
            )
        )
    return tuple(output)


def _cluster_merges(correlation, input_ids):
    clusters = [tuple((item,)) for item in input_ids]
    index = {item: position for position, item in enumerate(input_ids)}
    output = []
    while len(clusters) > 1:
        candidates = []
        for left_index, right_index in combinations(range(len(clusters)), 2):
            left = clusters[left_index]
            right = clusters[right_index]
            distances = [
                1.0 - abs(correlation[index[a], index[b]])
                for a in left
                for b in right
            ]
            candidates.append(
                (float(np.mean(distances)), tuple(sorted((*left, *right))), left_index, right_index)
            )
        distance, _, left_index, right_index = min(candidates)
        left = clusters[left_index]
        right = clusters[right_index]
        merged = tuple(sorted((*left, *right)))
        output.append(
            FactorSpaceClusterMergeV1(
                step=len(output) + 1,
                left_members=left,
                right_members=right,
                merged_members=merged,
                distance=_decimal(distance),
            )
        )
        clusters = [
            item for position, item in enumerate(clusters) if position not in {left_index, right_index}
        ]
        clusters.append(merged)
        clusters.sort()
    return tuple(output)


def _pca(values, input_ids, *, rank, condition_status, condition_number):
    _, singular, vt = np.linalg.svd(values, full_matrices=False)
    eigenvalues = np.square(singular) / (values.shape[0] - 1)
    total = float(eigenvalues.sum())
    ratios = eigenvalues / total
    cumulative = np.cumsum(ratios)
    components = []
    for component_index in range(len(input_ids)):
        loadings = vt[component_index].copy()
        pivot = int(np.argmax(np.abs(loadings)))
        if loadings[pivot] < 0.0:
            loadings *= -1.0
        components.append(
            FactorSpaceComponentV1(
                component=component_index + 1,
                eigenvalue=_decimal(eigenvalues[component_index]),
                explained_variance_ratio=_decimal(ratios[component_index]),
                cumulative_explained_variance_ratio=_decimal(cumulative[component_index]),
                loadings=tuple(
                    FactorSpaceLoadingV1(input_id=input_id, loading=_decimal(loadings[index]))
                    for index, input_id in enumerate(input_ids)
                ),
            )
        )
    participation = total * total / float(np.square(eigenvalues).sum())
    dimension = FactorSpaceDimensionV1(
        numerical_rank=rank,
        participation_ratio=_decimal(participation),
        kaiser_count=int((eigenvalues > 1.0).sum()),
        components_80=_threshold_count(cumulative, 0.80),
        components_90=_threshold_count(cumulative, 0.90),
        components_95=_threshold_count(cumulative, 0.95),
        condition_status=condition_status,
        condition_number=condition_number,
    )
    return tuple(components), dimension


def _threshold_count(cumulative, threshold):
    return int(np.searchsorted(cumulative, threshold, side="left") + 1)


def _average_ranks(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def _decimal(value: float) -> str:
    if not np.isfinite(value):
        raise FactorSpaceDiagnosticError("diagnostic value is non-finite")
    rounded = round(float(value), 10)
    if rounded == 0.0:
        rounded = 0.0
    return f"{rounded:.10f}"
