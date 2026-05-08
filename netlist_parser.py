import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional


KNOWN_COMPONENT_TYPES = {
    "POWER_SUPPLY",
    "GROUND",
    "MICROCONTROLLER",
    "LOGIC_IC",
    "VOLTAGE_REG",
    "LED",
    "RESISTOR",
    "CAPACITOR",
    "INDUCTOR",
    "MOSFET",
    "MOTOR",
    "SENSOR_IC",
    "DISPLAY",
    "STORAGE",
    "RELAY",
    "UNKNOWN",
}


def parse_board_file(file_path: str) -> Dict[str, Any]:
    """Choose a parser from the board/netlist extension."""
    lower_path = file_path.lower()
    if lower_path.endswith((".fbrd", ".sch")):
        return _parse_fusion_xml(file_path)
    if lower_path.endswith(".kicad_pcb"):
        return _parse_kicad_pcb(file_path)
    return parse_kicad_netlist(file_path)


def _parse_fusion_xml(file_path: str) -> Dict[str, Any]:
    """Parse Autodesk Fusion/EAGLE XML board files."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, IsADirectoryError, OSError) as e:
        print(f"[DEBUG] Failed to parse {file_path}, falling back to empty netlist: {e}", flush=True)
        return {
            "description": f"Failed parse of {file_path}. Empty netlist returned for safety.",
            "components": [],
            "netlist": [],
            "violations": [],
        }

    components = []
    component_map: Dict[str, Dict[str, Any]] = {}

    for elem in root.iter("element"):
        comp_id = elem.get("name", "UNKNOWN").strip()
        value = elem.get("value", "").strip()
        explicit_type = elem.get("type")
        comp_spec = _make_component_spec(comp_id, value, explicit_type)
        components.append(comp_spec)
        component_map[comp_id] = comp_spec

    netlist_connections = []
    for signal in root.iter("signal"):
        net_name = signal.get("name", "UNKNOWN_NET").strip()
        refs = [contact.get("element") for contact in signal.iter("contactref")]
        netlist_connections.extend(_connections_from_net(net_name, refs, component_map))

    return {
        "description": f"Autodesk Fusion XML parse of {file_path}.",
        "components": components,
        "netlist": netlist_connections,
        "violations": [],
    }


def _parse_kicad_pcb(file_path: str) -> Dict[str, Any]:
    """Parse enough KiCad board-layout S-expressions to recover components and nets."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise ValueError(f"Could not read file at {file_path}")

    if not raw.strip():
        raise ValueError("KiCad PCB file is empty.")

    try:
        tree = _parse_sexp(raw)
    except ValueError:
        data = parse_kicad_netlist(file_path)
        data["description"] = f"KiCad Physical Layout (.kicad_pcb) parse of {file_path}."
        return data

    components: List[Dict[str, Any]] = []
    component_map: Dict[str, Dict[str, Any]] = {}
    net_refs: Dict[str, List[str]] = {}

    for footprint in _walk_tag(tree, "footprint"):
        ref = _property_value(footprint, "Reference") or _child_value(footprint, "reference")
        value = _property_value(footprint, "Value") or ""
        if not ref:
            continue
        comp_spec = _make_component_spec(ref, value)
        components.append(comp_spec)
        component_map[ref] = comp_spec

        for pad in _children(footprint, "pad"):
            net_entry = _first_child(pad, "net")
            if not net_entry or len(net_entry) < 3:
                continue
            net_name = str(net_entry[2])
            net_refs.setdefault(net_name, []).append(ref)

    netlist_connections = []
    for net_name, refs in net_refs.items():
        netlist_connections.extend(_connections_from_net(net_name, refs, component_map))

    return {
        "description": f"KiCad Physical Layout (.kicad_pcb) parse of {file_path}.",
        "components": components,
        "netlist": netlist_connections,
        "violations": [],
    }


def parse_kicad_netlist(netlist_path: str) -> Dict[str, Any]:
    try:
        with open(netlist_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raise ValueError(f"Could not read file at {netlist_path}")

    if not raw.strip():
        raise ValueError("Netlist file is empty.")

    try:
        tree = _parse_sexp(raw)
        return _parse_kicad_export_tree(tree, netlist_path)
    except ValueError:
        return _parse_kicad_netlist_legacy_regex(raw, netlist_path)


def _parse_kicad_export_tree(tree: Any, netlist_path: str) -> Dict[str, Any]:
    components_section = _first_child(tree, "components")
    nets_section = _first_child(tree, "nets")
    if not components_section or not nets_section:
        raise ValueError("KiCad export sections not found.")

    components = []
    component_map: Dict[str, Dict[str, Any]] = {}

    for comp in _children(components_section, "comp"):
        ref = _child_value(comp, "ref")
        if not ref:
            continue
        value = _child_value(comp, "value") or ""
        explicit_type = _child_value(comp, "type")
        comp_spec = _make_component_spec(ref, value, explicit_type)
        components.append(comp_spec)
        component_map[ref] = comp_spec

    netlist_connections = []
    for net in _children(nets_section, "net"):
        net_name = _child_value(net, "name") or "UNKNOWN_NET"
        refs = [_child_value(node, "ref") for node in _children(net, "node")]
        netlist_connections.extend(_connections_from_net(net_name, refs, component_map))

    return {
        "description": f"Audit PCB netlist parsed from {netlist_path}.",
        "components": components,
        "netlist": netlist_connections,
        "violations": [],
    }


def _parse_kicad_netlist_legacy_regex(raw: str, netlist_path: str) -> Dict[str, Any]:
    """Fallback for malformed exports. The S-expression parser is preferred."""
    components = []
    component_map: Dict[str, Dict[str, Any]] = {}

    comp_blocks = re.findall(
        r"\(comp\s+[\s\S]*?\(ref\s+([^\s\)]+)\)[\s\S]*?\(value\s+\"?([^\"\)]+)\"?\)[\s\S]*?\)",
        raw,
    )

    for ref, value in comp_blocks:
        comp_spec = _make_component_spec(ref.strip(), value.strip())
        components.append(comp_spec)
        component_map[comp_spec["id"]] = comp_spec

    net_matches = re.findall(
        r"\(net\s+\(code\s+\d+\)\s+\(name\s+\"?([^\"\)]+)\"?\)(.*?)\n\s*\)",
        raw,
        re.DOTALL,
    )
    netlist_connections = []
    for net_name, nodes_raw in net_matches:
        refs = [ref for ref, _ in re.findall(r"\(node\s+\(ref\s+([^\s\)]+)\)\s+\(pin\s+\"?([^\"\)]+)\"?\)\)", nodes_raw)]
        netlist_connections.extend(_connections_from_net(net_name, refs, component_map))

    return {
        "description": f"Audit PCB netlist parsed from {netlist_path}.",
        "components": components,
        "netlist": netlist_connections,
        "violations": [],
    }


def _make_component_spec(comp_id: str, value: str, explicit_type: Optional[str] = None) -> Dict[str, Any]:
    inferred_type = _infer_component_type(value, comp_id)
    normalized_type = _normalize_component_type(explicit_type)
    comp_type = inferred_type if inferred_type != "UNKNOWN" else (normalized_type or "UNKNOWN")
    comp_spec = {
        "id": comp_id,
        "type": comp_type,
        "voltage": None,
        "max_input_voltage": None,
        "max_current_ma": None,
    }
    _apply_heuristics(comp_spec, comp_type, value, comp_id)
    return comp_spec


def _normalize_component_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")
    aliases = {
        "MCU": "MICROCONTROLLER",
        "MICRO": "MICROCONTROLLER",
        "SENSOR": "SENSOR_IC",
        "DISPLAY_IC": "DISPLAY",
        "REGULATOR": "VOLTAGE_REG",
        "VREG": "VOLTAGE_REG",
        "POWER": "POWER_SUPPLY",
        "SUPPLY": "POWER_SUPPLY",
        "GND": "GROUND",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in KNOWN_COMPONENT_TYPES else None


def _apply_heuristics(comp_spec: Dict[str, Any], comp_type: str, value: str, comp_id: str = "") -> None:
    """Fill standard electrical limits from the inferred component type."""
    text = f"{comp_id} {value}"
    if comp_type == "POWER_SUPPLY":
        comp_spec["voltage"] = _extract_voltage(text)
    elif comp_type == "GROUND":
        comp_spec["voltage"] = 0.0
    elif comp_type == "MICROCONTROLLER":
        comp_spec.update({"max_input_voltage": 3.6, "max_current_ma": 500})
    elif comp_type == "LOGIC_IC":
        comp_spec.update({"max_input_voltage": 5.5, "max_current_ma": 200})
    elif comp_type == "VOLTAGE_REG":
        comp_spec.update({"voltage": _extract_voltage(text) or 3.3, "max_input_voltage": 30.0, "max_current_ma": 1000})
    elif comp_type == "SENSOR_IC":
        comp_spec.update({"max_input_voltage": 5.0, "max_current_ma": 100})
    elif comp_type == "DISPLAY":
        comp_spec.update({"max_input_voltage": 3.6, "max_current_ma": 150})
    elif comp_type == "STORAGE":
        comp_spec.update({"max_input_voltage": 3.6, "max_current_ma": 150})
    elif comp_type == "LED":
        comp_spec.update({"max_input_voltage": 5.0, "max_current_ma": 20})
    elif comp_type == "RESISTOR":
        comp_spec.update({"max_input_voltage": 50.0, "max_current_ma": 200})
    elif comp_type == "RELAY":
        comp_spec.update({"max_input_voltage": _extract_voltage(text) or 12.0, "max_current_ma": 500})
    elif comp_type == "MOTOR":
        comp_spec.update({"max_input_voltage": _extract_voltage(text) or 12.0, "max_current_ma": 2000})
    elif comp_type == "MOSFET":
        comp_spec.update({"max_input_voltage": 30.0, "max_current_ma": 3000})


def _infer_component_type(value: str, comp_id: str = "") -> str:
    text = f"{comp_id} {value}".lower()
    compact = re.sub(r"[^a-z0-9]+", "", text)
    ref = comp_id.upper()

    if ref in {"GND", "GROUND", "VSS", "GND_REF"} or value.strip().lower() in {"gnd", "ground", "vss"}:
        return "GROUND"
    if any(p in compact for p in ("stm32", "atmega", "esp32", "arduino", "mcu", "microcontroller", "pic", "arm")):
        return "MICROCONTROLLER"
    if any(p in compact for p in ("rfid", "sensor", "bme280", "bmp180", "dht", "imu", "accelerometer")):
        return "SENSOR_IC"
    if any(p in compact for p in ("motor", "dcmotor", "stepper")) or ref.startswith("M"):
        return "MOTOR"
    if any(p in compact for p in ("mosfet", "transistor", "fet")) or ref.startswith("Q"):
        return "MOSFET"
    if any(p in compact for p in ("relay", "contactor")) or ref.startswith("K"):
        return "RELAY"
    if any(p in compact for p in ("oled", "lcd", "display")):
        return "DISPLAY"
    if any(p in compact for p in ("sdcard", "flash", "eeprom", "storage")):
        return "STORAGE"
    if any(p in compact for p in ("ldo", "lm1117", "ams1117", "regulator", "vreg")) or re.search(r"\d+(\.\d+)?v_?reg", text):
        return "VOLTAGE_REG"
    if any(p in compact for p in ("vcc", "vdd", "v5v", "v3v3", "vinput", "vmot", "vbat", "battery", "supply", "psu")):
        return "POWER_SUPPLY"
    if re.search(r"\b(74hc|74ls|logic|nand|xor|and_gate|or_gate)\b", text):
        return "LOGIC_IC"
    if ref.startswith("R") or re.search(r"\b\d+(\.\d+)?\s*(r|ohm|k|kiloohm|mohm)\b", text):
        return "RESISTOR"
    if ref.startswith("C") or re.search(r"\b\d+(\.\d+)?\s*(uf|nf|pf)\b", text):
        return "CAPACITOR"
    if ref.startswith("L") or re.search(r"\b\d+(\.\d+)?\s*(mh|uh|nh)\b", text):
        return "INDUCTOR"
    if ref.startswith("D") or "led" in compact:
        return "LED"
    return "UNKNOWN"


def _extract_voltage(value: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*v", value.lower())
    return float(match.group(1)) if match else None


def _connections_from_net(
    net_name: str,
    refs: Iterable[Optional[str]],
    component_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    unique_refs = _unique_refs(refs)
    if len(unique_refs) < 2:
        return []

    driver = _choose_net_driver(net_name, unique_refs, component_map)
    connections = []
    for ref in unique_refs:
        if ref == driver:
            continue
        src_comp = component_map.get(driver, {})
        dst_comp = component_map.get(ref, {})
        protection = not _is_direct_power_path(driver, ref, net_name, component_map)
        connections.append(
            {
                "from": driver,
                "to": ref,
                "net": net_name,
                "current_ma": _estimate_current(src_comp, dst_comp),
                "protection": protection,
            }
        )
    return connections


def _unique_refs(refs: Iterable[Optional[str]]) -> List[str]:
    seen = set()
    unique = []
    for ref in refs:
        if not ref:
            continue
        clean = str(ref).strip()
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique


def _choose_net_driver(net_name: str, refs: List[str], component_map: Dict[str, Dict[str, Any]]) -> str:
    net_upper = net_name.upper()
    if "GND" in net_upper or "GROUND" in net_upper:
        for ref in refs:
            if component_map.get(ref, {}).get("type") == "GROUND":
                return ref

    for wanted_type in ("POWER_SUPPLY", "VOLTAGE_REG"):
        for ref in refs:
            if component_map.get(ref, {}).get("type") == wanted_type:
                return ref

    for ref in refs:
        if component_map.get(ref, {}).get("voltage") is not None:
            return ref

    return refs[0]


def _is_direct_power_path(src: str, dst: str, net: str, component_map: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    src_upper = src.upper()
    dst_upper = dst.upper()
    net_upper = net.upper()
    types = {
        component_map.get(src, {}).get("type") if component_map else None,
        component_map.get(dst, {}).get("type") if component_map else None,
    }
    power_names = ("VCC", "VDD", "V5V", "V3V3", "VINPUT", "VMOT", "VBAT", "PWR")
    ground_names = ("GND", "VSS", "GROUND")
    has_power = "POWER_SUPPLY" in types or any(p in src_upper or p in dst_upper for p in power_names)
    has_ground = "GROUND" in types or any(g in src_upper or g in dst_upper for g in ground_names)
    suspicious_net = any(kw in net_upper for kw in ("SHORT", "DIRECT", "BYPASS"))
    return bool(has_power and has_ground and suspicious_net)


def _estimate_current(src_comp: Dict[str, Any], dst_comp: Dict[str, Any]) -> int:
    src_type = src_comp.get("type", "UNKNOWN")
    dst_type = dst_comp.get("type", "UNKNOWN")
    if src_type == "POWER_SUPPLY":
        if dst_type == "MICROCONTROLLER":
            return 500
        if dst_type == "MOTOR":
            return 1800
        if dst_type == "VOLTAGE_REG":
            return 800
        if dst_type in ("LED", "RESISTOR"):
            return 20
        return 100
    if src_type == "VOLTAGE_REG":
        if dst_type == "MICROCONTROLLER":
            return 100
        if dst_type in ("DISPLAY", "STORAGE", "SENSOR_IC"):
            return 100
        return 250
    return 50


def _parse_sexp(raw: str) -> Any:
    raw = raw.lstrip("\ufeff")
    tokens = re.findall(r'"(?:\\.|[^"])*"|[()]|[^\s()]+', raw)
    if not tokens:
        raise ValueError("No S-expression tokens found.")
    expr, pos = _read_sexp(tokens, 0)
    if pos != len(tokens):
        raise ValueError("Trailing tokens in S-expression.")
    return expr


def _read_sexp(tokens: List[str], pos: int) -> Any:
    if pos >= len(tokens):
        raise ValueError("Unexpected end of S-expression.")
    token = tokens[pos]
    if token == "(":
        pos += 1
        items = []
        while pos < len(tokens) and tokens[pos] != ")":
            child, pos = _read_sexp(tokens, pos)
            items.append(child)
        if pos >= len(tokens):
            raise ValueError("Unclosed S-expression.")
        return items, pos + 1
    if token == ")":
        raise ValueError("Unexpected closing parenthesis.")
    return _decode_atom(token), pos + 1


def _decode_atom(token: str) -> str:
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return bytes(token[1:-1], "utf-8").decode("unicode_escape")
    return token


def _children(expr: Any, tag: str) -> List[List[Any]]:
    if not isinstance(expr, list):
        return []
    return [child for child in expr[1:] if isinstance(child, list) and child and child[0] == tag]


def _first_child(expr: Any, tag: str) -> Optional[List[Any]]:
    matches = _children(expr, tag)
    return matches[0] if matches else None


def _child_value(expr: Any, tag: str) -> Optional[str]:
    child = _first_child(expr, tag)
    if child and len(child) >= 2:
        return str(child[1])
    return None


def _walk_tag(expr: Any, tag: str) -> Iterable[List[Any]]:
    if isinstance(expr, list):
        if expr and expr[0] == tag:
            yield expr
        for child in expr[1:]:
            yield from _walk_tag(child, tag)


def _property_value(expr: Any, property_name: str) -> Optional[str]:
    for prop in _children(expr, "property"):
        if len(prop) >= 3 and str(prop[1]).lower() == property_name.lower():
            return str(prop[2])
    return None
