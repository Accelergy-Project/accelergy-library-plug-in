from accelergy.plug_in_interface.interface import (
    AccelergyPlugIn,
    Estimation,
    AccuracyEstimation,
    AccelergyQuery,
)
from accelergy.plug_in_interface.estimator_wrapper import (
    SupportedComponent,
    PrintableCall,
)
from typing import Dict, List, Tuple, Union
import os
import sys

# fmt: off for Black formatter
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(SCRIPT_DIR)
from scaling import *
from helper_functions import *

# fmt: on

AREA_ACCURACY = 90
ENERGY_ACCURACY = 90

# =============================================================================
# Wrapper Class
# =============================================================================


class LibraryEstimator(AccelergyPlugIn):
    def __init__(self):
        self.estimator_name = "Library"
        super().__init__()
        self.components = []

        component_files = [
            os.path.join(root, f)
            for root, _, files in os.walk(os.path.join(SCRIPT_DIR, "library"))
            for f in files
        ]

        for k, v in os.environ.items():
            if "ACCELERGY_COMPONENT_LIBRARIES" not in k:
                continue
            for path in v.split(","):
                component_files += [
                    os.path.join(root, f)
                    for root, _, files in os.walk(path)
                    for f in files
                ]

        self._load_component_files(component_files)
        self._load_reference_files(component_files)
        self.logger.info(f"Loaded {len(self.components)} components from library.")

        for c in self.components:
            c.setdefault("n_instances", 1)

        self.action2entry = {}
        self.name2entry = {}
        for c in self.components:
            for action in c["action"].split("|"):
                name = c["name"].lower().strip()
                action = action.lower().strip()
                entry = {**c, **{"name": name, "action": action}}
                self.action2entry.setdefault(
                    (entry["name"], entry["action"]), []
                ).append(entry)
                self.name2entry.setdefault(entry["name"], []).append(entry)

        # Make sure all components have a read, write, update, and leak action
        for name in self.name2entry:
            for action in ["read", "write", "update", "leak"]:
                assert (
                    name,
                    action,
                ) in self.action2entry, (
                    f"Missing {action} action for Library component {name}."
                )

    def _load_component_lines(self, name: str, lines: List[str]):
        """Loads the component lines into self.components"""
        keys = [k.strip() for k in lines[0].split(",")]
        last_nonempty = 0
        for i, k in enumerate(keys):
            if k:
                last_nonempty = i
        keys = keys[: last_nonempty + 1]

        for l in lines[1:]:
            if l:
                values = [v.strip() for v in l.split(",")]
                self.components.append(dict(zip(keys, values)))
                self.components[-1]["name"] = name.lower()

    def _load_component_files(self, files: List[str]):
        """Loads the component files into self.components"""
        component_files = [f for f in files if f.endswith(".csv")]
        for f in component_files:
            lines = [l.split("#")[0].strip() for l in open(f).readlines()]
            lines = [l for l in lines if l.replace(",", "")]

            curname = os.path.basename(f).split(".")[0]
            curlines = []
            for i, l in enumerate(lines):
                if "COMPONENT" in lines[i]:
                    if curlines:
                        self._load_component_lines(curname, curlines)
                        curlines = []
                    curname = l.split(":")[1].strip()
                else:
                    curlines.append(l)
            if curlines:
                self._load_component_lines(curname, curlines)

    def _load_reference_files(self, files: List[str]):
        """Loads the reference files into self.components"""
        references = {}
        reference_files = [f for f in files if f.endswith("_pointers.txt")]
        # Load references
        for ref in reference_files:
            lines = open(ref).readlines()
            for l in lines:
                k, v = l.split(":", maxsplit=1)
                references[k.strip().lower()] = v.strip().lower()

        # Find references in components
        for k, v in references.items():
            found = False
            for c in self.components:
                if c["name"] == v:
                    self.components.append({**c, **{"name": k}})
                    found = True
            if not found:
                raise ValueError(
                    f"Reference {k}->{v} not found. Known components:\n\t"
                    + "\n\t".join(c["name"] for c in self.components)
                )

    def primitive_action_supported(self, query: AccelergyQuery) -> AccuracyEstimation:
        success = self.get_energy_or_area(query, log_scaling=False) is not None
        return AccuracyEstimation(ENERGY_ACCURACY if success else 0)

    def primitive_area_supported(self, query: AccelergyQuery) -> AccuracyEstimation:
        success = self.estimate_area(query, log_scaling=False) is not None
        return AccuracyEstimation(AREA_ACCURACY if success else 0)

    def estimate_energy(self, query: AccelergyQuery, **kwargs) -> Estimation:
        return self.get_energy_or_area(query, True, **kwargs)

    def estimate_area(self, query: AccelergyQuery, **kwargs) -> Estimation:
        return self.get_energy_or_area(query, False, **kwargs)

    def get_name(self) -> str:
        return self.estimator_name

    def match_entry(
        self,
        query: AccelergyQuery,
        entry: Dict[str, str],
        target: str,
        log_scaling: bool,
    ) -> Tuple[Union[float, None], int, List[str]]:
        """Matches a query to an entry in the library. Returns the energy/area
        scale, the number of matching attributes, and a log."""
        class_name = query.class_name.lower()
        class_attrs = query.class_attrs
        scale, log = 1, []
        self.logger.info(f'Checking entry "{entry}')

        # Check if we match the attributes. Find those that must be scaled
        matching_attrs, attrs_to_scale = [], []

        def entrykey(a):
            for k in entry:
                if str(a).lower() == str(k).lower():
                    return k
                if str(a).lower() in str(k).lower().split("|"):
                    return k
            return None

        class2entry = {}
        for a in class_attrs:
            if entrykey(a) not in class2entry.values():
                class2entry[a] = entrykey(a)
            else:
                class2entry[a] = None

        for a in class_attrs:
            entry_val = entry.get(class2entry[a], None)
            if entry_val is None:
                pass
            elif (
                str(entry_val) == "*"
                or str(entry_val).lower() == str(class_attrs[a]).lower()
            ):
                matching_attrs.append(a)
            elif not class_attrs.get(f"no_scale_{target}", False):
                log.append(f"Scaling {a} from {entry_val} to {class_attrs[a]}")
                attrs_to_scale.append(a)

        # Scale the attributes that must be scaled
        try:
            # Try to scale the attributes that must be scaled
            for a in attrs_to_scale:
                scalefrom = parse_float(entry[class2entry[a]], f"{class_name}.{a}")
                scaleto = parse_float(class_attrs[a], f"{class_name}.{a}")
                s = scale_energy_or_area(a, scalefrom, scaleto, target)

                if s == 1:
                    matching_attrs.append(a)

                scale *= s
                if scale and log_scaling:
                    log.append(
                        f"Scaled {class_name}.{a} from {scalefrom} to "
                        f"{scaleto}: {s}x {target}"
                    )

        except (ValueError, ZeroDivisionError) as e:
            scale = None
            self.logger.info(f"Failed to scale {class_name}: {str(e).strip()}")

        return scale, len(matching_attrs), log

    def get_energy_or_area(
        self,
        query: AccelergyQuery,
        is_energy: bool = True,
        log_scaling: bool = True,
    ) -> Estimation:
        class_name = query.class_name.lower()
        # For finding closest-matching component
        best_value, best_matches, best_log, best_entry = None, -1, [], {}
        target = "energy" if is_energy else "area"
        get_value = target
        if query.action_name == "leak":
            target = "leak"

        if is_energy:
            action_name = query.action_name.lower()
            entries = self.action2entry.get((class_name, action_name), [])
            self.logger.info(
                f"Found {len(entries)} entries for {class_name}.{action_name}."
            )
        else:
            entries = self.name2entry.get(class_name, [])
            self.logger.info(f"Found {len(entries)} entries for {class_name}.")

        for entry in entries:
            scale, matching_attrs, log = self.match_entry(
                query, entry, target, log_scaling
            )
            if scale is None:
                continue

            # Scaled successfully! Now get the value
            if log_scaling:
                log.append(f"{class_name} {target} has been scaled {scale}x")

            value = get_value_from_entry(entry, get_value)
            self.logger.info(f"{value=}, {matching_attrs=}, {log=}")

            if value is not None and matching_attrs > best_matches:
                best_value = value * scale
                best_matches = matching_attrs
                best_log = log
                best_entry = entry

        if log_scaling:
            self.logger.info(f"Best-matching entry: {best_entry}")
            for l in best_log:
                self.logger.info(l)

        if best_value is None:
            raise ValueError(f"Could not find {target} for {class_name}")
        return Estimation(best_value, "p" if is_energy else "u^2")

    def get_supported_components(self) -> List[SupportedComponent]:
        supported = []
        for c in self.components:
            class_names = c["name"].split("|")
            c_popped = {k: v for k, v in c.items() if k not in ["name", "action"]}
            supported.append(
                SupportedComponent(
                    class_names,
                    PrintableCall("", [], c_popped),
                    [PrintableCall(a) for a in c["action"].split("|")],
                )
            )
        return supported


if __name__ == "__main__":
    s = LibraryEstimator()
