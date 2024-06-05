from math import ceil, floor
from typing import Union

# =============================================================================
# Technology node scaling
# =============================================================================
"""
CMOS scaling based on: Aaron Stillmaker, Bevan Baas, Scaling equations for the
accurate prediction of CMOS device performance from 180nm to 7nm, Integration,
Volume 58, 2017, Pages 74-81, ISSN 0167-9260,
https://doi.org/10.1016/j.vlsi.2017.02.002.
"""


# Scaling from tech node X to tech node Y involves multiplying area from
# AREA_SCALING[X][Y].
TECH_NODES = [130, 90, 65, 45, 32, 20, 16, 14, 10, 7]
AREA_SCALING = [
    [1, 0.44, 0.23, 0.16, 0.072, 0.033, 0.03, 0.027, 0.016, 0.0092],
    [2.3, 1, 0.53, 0.35, 0.16, 0.075, 0.067, 0.061, 0.036, 0.021],
    [4.3, 1.9, 1, 0.66, 0.31, 0.14, 0.13, 0.12, 0.068, 0.039],
    [6.4, 2.8, 1.5, 1, 0.46, 0.21, 0.19, 0.17, 0.1, 0.059],
    [14, 6.1, 3.3, 2.2, 1, 0.46, 0.41, 0.38, 0.22, 0.13],
    [30, 13, 7.1, 4.7, 2.2, 1, 0.89, 0.82, 0.48, 0.28],
    [34, 15, 7.9, 5.3, 2.4, 1.1, 1, 0.91, 0.54, 0.31],
    [37, 16, 8.7, 5.8, 2.7, 1.2, 1.1, 1, 0.59, 0.34],
    [63, 28, 15, 9.8, 4.5, 2.1, 1.9, 1.7, 1, 0.58],
    [110, 48, 25, 17, 7.8, 3.6, 3.2, 2.9, 1.7, 1],
]

# Scaling from tech node X to tech node Y involves multiplying energy by
# ENERGY_SCALING[Y][0]Vdd^2+ENERGY_SCALING[Y][1]Vdd+ENERGY_SCALING[Y][2] and
# dividing by
# ENERGY_SCALING[X][0]Vdd^2+ENERGY_SCALING[X][1]Vdd+ENERGY_SCALING[X][2]
ENERGY_SCALING = [
    [7.171, -6.709, 2.904],
    [4.762, -4.781, 2.092],
    [3.755, -4.398, 1.975],
    [1.103, -0.362, 0.2767],
    [0.9559, -0.7823, 0.471],
    [0.373, -0.1582, 0.04104],
    [0.2958, -0.1241, 0.03024],
    [0.2363, -0.09675, 0.02239],
    [0.2068, -0.09311, 0.02375],
    [0.1776, -0.09097, 0.02447],
]


def get_technology_node_index(tech_node: float) -> float:
    """Returns the index of the technology node in the TECH_NODES array.
    Interpolates if necessary."""
    larger_idx, smaller_idx = None, None
    for i, t in enumerate(TECH_NODES):
        if tech_node <= t:
            larger_idx = i
        if tech_node >= t:
            smaller_idx = i
            break

    failed = larger_idx is None or smaller_idx is None

    assert not failed, (
        f"Technology node {tech_node} nm not supported. Ensure all technology "
        f"nodes are in the range [{TECH_NODES[-1]} nm,1e-9, {TECH_NODES[0]} nm]"
    )
    l_node, s_node = TECH_NODES[larger_idx], TECH_NODES[smaller_idx]
    if larger_idx == smaller_idx:
        return larger_idx
    interp = (tech_node - s_node) / (l_node - s_node)
    return larger_idx + (smaller_idx - larger_idx) * interp


def get_tech_node_area_scale(from_node: float, to_node: float) -> float:
    """Returns the scaling factor for area from the technology node
    `from_node` to the technology node `to_node`. Interpolates if necessary."""
    x = get_technology_node_index(from_node)
    y = get_technology_node_index(to_node)

    # This does 2D linear interpolation
    return sum(
        [
            AREA_SCALING[floor(x)][floor(y)] * (1 - x % 1) * (1 - y % 1),
            AREA_SCALING[floor(x)][ceil(y)] * (1 - x % 1) * (y % 1),
            AREA_SCALING[ceil(x)][floor(y)] * (x % 1) * (1 - y % 1),
            AREA_SCALING[ceil(x)][ceil(y)] * (x % 1) * (y % 1),
        ]
    )


def get_tech_node_energy_scale(
    from_node: float, to_node: float, vdd: Union[float, None] = None
) -> float:
    """Returns the scaling factor for energy from the technology node
    `from_node` to the technology node `to_node`. Interpolates if necessary."""
    x = get_technology_node_index(from_node)
    y = get_technology_node_index(to_node)
    if vdd is None:
        vdd = 0.8
    # Outer sum does linear interpolation
    x_e_factor = sum(
        [
            # These sums do aVdd^2 + bVdd + c
            sum(ENERGY_SCALING[floor(x)][i] * vdd ** (2 - i) for i in range(3))
            * (1 - x % 1),
            sum(ENERGY_SCALING[ceil(x)][i] * vdd ** (2 - i) for i in range(3))
            * (x % 1),
        ]
    )
    # Outer sum does linear interpolation
    y_e_factor = sum(
        [
            # These sums do aVdd^2 + bVdd + c
            sum(ENERGY_SCALING[floor(y)][i] * vdd ** (2 - i) for i in range(3))
            * (1 - y % 1),
            sum(ENERGY_SCALING[ceil(y)][i] * vdd ** (2 - i) for i in range(3))
            * (y % 1),
        ]
    )

    return y_e_factor / x_e_factor


# =============================================================================
# General scaling functions
# =============================================================================


def scale_area(param: str, v0: float, v1: float) -> float:
    """Scales the area of a component from "param" value v0 to v1."""

    # Linear scaling
    if param in [
        "width",
        "datawidth",
        "depth",
        "rows",
        "cols",
        "columns",
        "width_a",
        "width_b",
        "datawidth_a",
        "datawidth_b",
        "datawidth",
    ]:
        return v1 / v0

    # No scaling
    if param in [
        "energy_scale",
        "average_input_value",
        "average_weight_value",
        "average_output_value",
        "no_scale_area",
        "no_scale_energy",
        "voltage",
        "n_instances",
        "global_cycle_seconds",
        "area_scale",
        "energy_scale",
        "n_instances",
    ]:
        return 1

    # Custom scaling
    if param == "technology":
        return get_tech_node_area_scale(v0, v1)

    if param == "resolution":
        return 2 ** (v1 - v0)

    raise ValueError(f"Scaling of paramter {param} not supported.")


def scale_energy(param: str, v0: float, v1: float) -> float:
    """Scales the energy of a component from "param" value v0 to v1."""
    # Linear scaling
    if param in [
        "width",
        "datawidth",
        "average_input_value",
        "average_weight_value",
        "average_output_value",
        "width_a",
        "width_b",
        "datawidth_a",
        "datawidth_b",
        "datawidth",
        "n_steps",
    ]:
        return v1 / v0

    # No scaling
    if param in [
        "rows",
        "cols",
        "columns",
        "area_scale",
        "energy_scale",
        "n_instances",
        "no_scale_area",
        "no_scale_energy",
        "n_instances",
        "global_cycle_seconds",
    ]:
        return 1

    # Custom scaling
    if param == "depth":
        return (v1 / v0) ** (1.56 / 2)  # Based on CACTI scaling
    if param == "technology":
        return get_tech_node_energy_scale(v0, v1)
    if param == "resolution":
        return 2 ** (v1 - v0)
    if param == "voltage":
        return (v1 / v0) ** 2
    raise ValueError(f"Scaling of paramter {param} not supported.")


def scale_leak(param: str, v0: float, v1: float) -> float:
    if param == "voltage":
        return 1
    if param in ["global_cycle_seconds"]:
        return v1 / v0
    return scale_energy(param, v0, v1)


def scale_energy_or_area(param: str, v0: float, v1: float, target: str) -> float:
    param = param.lower()
    target = target.lower()
    """Scales the energy or area of a component from "param" value v0 to v1."""
    if target == "area":
        return scale_area(param, v0, v1)
    if target == "energy":
        return scale_energy(param, v0, v1)
    if target == "leak":
        return scale_leak(param, v0, v1)
    raise ValueError(f'Target {target} not supported. Use "area", "energy", or "leak.')


if __name__ == "__main__":
    print(get_tech_node_energy_scale(45, 22, 0.7))
    for x in TECH_NODES:
        print(x, get_tech_node_energy_scale(130, x))
