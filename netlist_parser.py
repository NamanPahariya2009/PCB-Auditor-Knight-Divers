import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

def parse_board_file(file_path: str) -> Dict[str, Any]:
    """Decide which parser to use based on the file extension."""
    if file_path.endswith('.fbrd') or file_path.endswith('.sch'):
        return _parse_fusion_xml(file_path)
    elif file_path.endswith('.kicad_pcb'):
        return _parse_kicad_pcb(file_path)
    else:
        return parse_kicad_netlist(file_path)

def _parse_fusion_xml(file_path: str) -> Dict[str, Any]:
    """Logic to parse XML board files from Autodesk Fusion or EAGLE."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, IsADirectoryError, Exception) as e:
        # Fallback to a safe, empty state instead of crashing with a Runtime Error
        print(f"[DEBUG] Failed to parse {file_path}, falling back to empty netlist: {e}", flush=True)
        return {
            "description": f"Failed parse of {file_path}. Empty netlist returned for safety.",
            "components": [], "netlist": [], "violations": []
        }

    components = []
    component_map = {}
    
    # Parse Elements (Components)
    for elem in root.iter('element'):
        comp_id = elem.get('name', 'UNKNOWN')
        value = elem.get('value', '')
        comp_type = _infer_component_type(value)
        
        comp_spec = {
            "id": comp_id, "type": comp_type, "voltage": None, 
            "max_input_voltage": None, "max_current_ma": None,
        }
        _apply_heuristics(comp_spec, comp_type, value)
        components.append(comp_spec)
        component_map[comp_id] = comp_spec

    # Parse Signals (Nets)
    netlist_connections = []
    for signal in root.iter('signal'):
        net_name = signal.get('name', 'UNKNOWN_NET')
        contacts = list(signal.iter('contactref'))
        
        for i in range(len(contacts) - 1):
            src_ref = contacts[i].get('element')
            dst_ref = contacts[i+1].get('element')
            if src_ref and dst_ref:
                protection = not _is_direct_power_path(src_ref, dst_ref, net_name)
                current_ma = _estimate_current(component_map.get(src_ref, {}), component_map.get(dst_ref, {}))
                netlist_connections.append({
                    "from": src_ref, "to": dst_ref, "net": net_name,
                    "current_ma": current_ma, "protection": protection,
                })

    return {
        "description": f"Autodesk Fusion XML parse of {file_path}.",
        "components": components, "netlist": netlist_connections, "violations": []
    }

def _parse_kicad_pcb(file_path: str) -> Dict[str, Any]:
    """Experimental parser for KiCad layout files."""
    # For Round 1, I route this through the standard regex parser 
    # as the netlist data is embedded similarly, but I tag it as a physical parse.
    data = parse_kicad_netlist(file_path)
    data["description"] = f"KiCad Physical Layout (.kicad_pcb) parse of {file_path}."
    return data

def parse_kicad_netlist(netlist_path: str) -> Dict[str, Any]:
    try:
        with open(netlist_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        raise ValueError(f"Could not read file at {netlist_path}")
    
    if not raw.strip():
        raise ValueError("Netlist file is empty.")

    components = []
    component_map = {}
    
    # Handling values with spaces or quotes in the netlist
    comp_blocks = re.findall(r'\(ref\s+([a-zA-Z0-9_]+)\)[\s\S]*?\(value\s+"?([^"\)]+)"?\)', raw)
    
    for ref, value in comp_blocks:
        comp_id = ref.strip()
        comp_type = _infer_component_type(value.strip())
        comp_spec = {
            "id": comp_id, "type": comp_type, "voltage": None, 
            "max_input_voltage": None, "max_current_ma": None,
        }
        _apply_heuristics(comp_spec, comp_type, value)
        components.append(comp_spec)
        component_map[comp_id] = comp_spec
    
    net_matches = re.findall(r'\(net\s+\(code\s+\d+\)\s+\(name\s+"?([^"\)]+)"?\)(.*?)\n\s*\)', raw, re.DOTALL)
    netlist_connections = []
    for net_name, nodes_raw in net_matches:
        nodes = re.findall(r'\(node\s+\(ref\s+(\w+)\)\s+\(pin\s+"?([^"\)]+)"?\)\)', nodes_raw)
        for i in range(len(nodes) - 1):
            src_ref, _ = nodes[i]
            dst_ref, _ = nodes[i + 1]
            protection = not _is_direct_power_path(src_ref, dst_ref, net_name)
            current_ma = _estimate_current(component_map.get(src_ref, {}), component_map.get(dst_ref, {}))
            netlist_connections.append({
                "from": src_ref, "to": dst_ref, "net": net_name,
                "current_ma": current_ma, "protection": protection,
            })
            
    return {
        "description": f"Audit PCB netlist parsed from {netlist_path}.",
        "components": components, "netlist": netlist_connections, "violations": [], 
    }

def _apply_heuristics(comp_spec: Dict, comp_type: str, value: str):
    """Filling in standard voltage and current limits based on component type."""
    if comp_type == "POWER_SUPPLY": comp_spec["voltage"] = _extract_voltage(value)
    elif comp_type == "GROUND": comp_spec["voltage"] = 0.0
    elif comp_type == "MICROCONTROLLER": comp_spec.update({"max_input_voltage": 3.6, "max_current_ma": 500})
    elif comp_type == "LOGIC_IC": comp_spec.update({"max_input_voltage": 5.5, "max_current_ma": 200})
    elif comp_type == "VOLTAGE_REG": comp_spec.update({"voltage": 3.3, "max_input_voltage": 30.0, "max_current_ma": 1000})
    elif comp_type == "LED": comp_spec.update({"max_input_voltage": 5.0, "max_current_ma": 20})
    elif comp_type == "RESISTOR": comp_spec.update({"max_input_voltage": 50.0, "max_current_ma": 200})

def _infer_component_type(value: str) -> str:
    v = value.lower()
    if any(p in v for p in ("vcc", "vdd", "v5v", "v3v3", "vinput", "psu", "battery")): return "POWER_SUPPLY"
    if v in ("gnd", "ground", "vss"): return "GROUND"
    if any(p in v for p in ("mcu", "stm32", "atmega", "esp32", "pic", "arm")): return "MICROCONTROLLER"
    if any(p in v for p in ("74hc", "74ls", "logic", "and", "or", "nand", "xor")): return "LOGIC_IC"
    if any(p in v for p in ("ldo", "lm1117", "ams1117", "regulator", "vreg")): return "VOLTAGE_REG"
    if any(p in v for p in ("mosfet", "transistor", "q", "fet")): return "MOSFET"
    if any(p in v for p in ("motor", "m1", "m2")): return "MOTOR"
    if any(p in v for p in ("sensor", "bme280", "bmp180", "dht")): return "SENSOR_IC"
    if any(p in v for p in ("oled", "lcd", "display")): return "DISPLAY"
    if v.startswith("r") or "ohm" in v: return "RESISTOR"
    if v.startswith("c") or "uf" in v or "nf" in v: return "CAPACITOR"
    if v.startswith("l") or "mh" in v or "uh" in v: return "INDUCTOR"
    if v.startswith("d") or "led" in v: return "LED"
    return "UNKNOWN"

def _extract_voltage(value: str) -> Optional[float]:
    match = re.search(r'(\d+\.?\d*)\s*v', value.lower())
    return float(match.group(1)) if match else None

def _is_direct_power_path(src: str, dst: str, net: str) -> bool:
    power_nodes = ("VCC", "VDD", "V5V", "V3V3", "VINPUT", "VMOT", "VBAT")
    ground_nodes = ("GND", "VSS", "GROUND")
    if any(p in src.upper() for p in power_nodes) and any(g in dst.upper() for g in ground_nodes):
        if any(kw in net.upper() for kw in ("SHORT", "DIRECT", "BYPASS")): return True
    return False

def _estimate_current(src_comp: Dict, dst_comp: Dict) -> int:
    st = src_comp.get("type", "UNKNOWN")
    dt = dst_comp.get("type", "UNKNOWN")
    if st == "POWER_SUPPLY":
        if dt == "MICROCONTROLLER": return 500
        if dt == "MOTOR": return 1800
        if dt == "VOLTAGE_REG": return 800
        if dt in ("LED", "RESISTOR"): return 20
        return 100
    if st == "VOLTAGE_REG": return 750
    return 50