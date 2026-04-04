"""
netlist_parser.py — KiCad .net File Parser
Knight Divers | Naman Pahariya & Kapish Gupta

Parses standard KiCad netlist format (.net files) into PCBAuditorEnv-compatible JSON.

KiCad netlist structure:
(export (version D)
  (components
    (comp (ref U1) (value MCU) ...)
    (comp (ref R1) (value 10k) ...)
  )
  (nets
    (net (code 1) (name VCC)
      (node (ref U1) (pin 1))
      (node (ref R1) (pin 1))
    )
  )
)
"""

import re
from typing import Any, Dict, List, Optional


def parse_kicad_netlist(netlist_path: str) -> Dict[str, Any]:
    """
    Parse KiCad .net file into PCBAuditorEnv-compatible task format.
    
    Returns:
        dict: {
            "description": str,
            "components": List[Dict],
            "netlist": List[Dict],
            "violations": List[str],
        }
    """
    with open(netlist_path, "r", encoding="utf-8") as f:
        raw = f.read()
    
    # Simple S-expression parser for components
    components = []
    component_map = {}
    
    # Find all (comp ...) blocks
    comp_blocks = re.findall(r'\(comp\s+\(ref\s+(\w+)\)\s+\(value\s+([\w\-\_\.]+)\)', raw)
    
    for ref, value in comp_blocks:
        comp_id = ref.strip()
        comp_type = _infer_component_type(value.strip())
        
        # Build component spec
        comp_spec = {
            "id": comp_id,
            "type": comp_type,
            "voltage": None,
            "max_input_voltage": None,
            "max_current_ma": None,
        }
        
        # Assign default ratings based on type heuristics
        if comp_type == "POWER_SUPPLY":
            comp_spec["voltage"] = _extract_voltage(value)
        elif comp_type == "GROUND":
            comp_spec["voltage"] = 0.0
        elif comp_type == "MICROCONTROLLER":
            comp_spec["max_input_voltage"] = 3.6
            comp_spec["max_current_ma"] = 500
        elif comp_type == "LOGIC_IC":
            comp_spec["max_input_voltage"] = 5.5
            comp_spec["max_current_ma"] = 200
        elif comp_type == "VOLTAGE_REG":
            comp_spec["voltage"] = 3.3
            comp_spec["max_input_voltage"] = 30.0
            comp_spec["max_current_ma"] = 1000
        elif comp_type == "LED":
            comp_spec["max_input_voltage"] = 5.0
            comp_spec["max_current_ma"] = 20
        elif comp_type == "RESISTOR":
            comp_spec["max_input_voltage"] = 50.0
            comp_spec["max_current_ma"] = 200
        
        components.append(comp_spec)
        component_map[comp_id] = comp_spec
    
    # Find all (net ...) blocks
    # Format: (net (code N) (name NETNAME) (node (ref U1) (pin 1)) (node (ref R1) (pin 2)) )
    net_pattern = r'\(net\s+\(code\s+\d+\)\s+\(name\s+([\w\-\_\/]+)\)(.*?)\n\s*\)'
    net_matches = re.findall(net_pattern, raw, re.DOTALL)
    
    netlist_connections = []
    
    for net_name, nodes_raw in net_matches:
        # Extract all node references in this net
        node_pattern = r'\(node\s+\(ref\s+(\w+)\)\s+\(pin\s+(\w+)\)\)'
        nodes = re.findall(node_pattern, nodes_raw)
        
        # Build pairwise connections (each node connects to next in the net)
        for i in range(len(nodes) - 1):
            src_ref, src_pin = nodes[i]
            dst_ref, dst_pin = nodes[i + 1]
            
            # Determine if this connection has protection (heuristic: fuse/ferrite in path)
            protection = not _is_direct_power_path(src_ref, dst_ref, net_name)
            
            # Estimate current (heuristic based on component types)
            current_ma = _estimate_current(
                component_map.get(src_ref, {}),
                component_map.get(dst_ref, {}),
            )
            
            netlist_connections.append({
                "from": src_ref,
                "to": dst_ref,
                "net": net_name,
                "current_ma": current_ma,
                "protection": protection,
            })
    
    # Build final task
    task = {
        "description": f"Audit PCB netlist parsed from {netlist_path}. Find all violations.",
        "components": components,
        "netlist": netlist_connections,
        "violations": [],  # Unknown until agent runs
    }
    
    return task


def _infer_component_type(value: str) -> str:
    """Infer component type from KiCad value field."""
    value_lower = value.lower()
    
    # Power sources
    if any(p in value_lower for p in ("vcc", "vdd", "v5v", "v3v3", "vinput", "psu", "battery")):
        return "POWER_SUPPLY"
    if value_lower in ("gnd", "ground", "vss"):
        return "GROUND"
    
    # Active components
    if any(p in value_lower for p in ("mcu", "stm32", "atmega", "esp32", "pic", "arm")):
        return "MICROCONTROLLER"
    if any(p in value_lower for p in ("74hc", "74ls", "logic", "and", "or", "nand", "xor")):
        return "LOGIC_IC"
    if any(p in value_lower for p in ("ldo", "lm1117", "ams1117", "regulator", "vreg")):
        return "VOLTAGE_REG"
    if any(p in value_lower for p in ("mosfet", "transistor", "q", "fet")):
        return "MOSFET"
    if any(p in value_lower for p in ("motor", "m1", "m2")):
        return "MOTOR"
    if any(p in value_lower for p in ("sensor", "bme280", "bmp180", "dht")):
        return "SENSOR_IC"
    if any(p in value_lower for p in ("oled", "lcd", "display")):
        return "DISPLAY"
    
    # Passives
    if value_lower.startswith("r") or "ohm" in value_lower:
        return "RESISTOR"
    if value_lower.startswith("c") or "uf" in value_lower or "nf" in value_lower:
        return "CAPACITOR"
    if value_lower.startswith("l") or "mh" in value_lower or "uh" in value_lower:
        return "INDUCTOR"
    if value_lower.startswith("d") or "led" in value_lower:
        return "LED"
    
    return "UNKNOWN"


def _extract_voltage(value: str) -> Optional[float]:
    """Extract voltage rating from component value string."""
    # Match patterns like "VCC_5V", "3V3", "12V", "V5V"
    match = re.search(r'(\d+\.?\d*)\s*v', value.lower())
    if match:
        return float(match.group(1))
    return None


def _is_direct_power_path(src: str, dst: str, net: str) -> bool:
    """
    Heuristic: Check if this is a dangerous unprotected power path.
    Returns True if path is direct power-to-ground without protection.
    """
    power_nodes = ("VCC", "VDD", "V5V", "V3V3", "VINPUT", "VMOT", "VBAT")
    ground_nodes = ("GND", "VSS", "GROUND")
    
    src_is_power = any(p in src.upper() for p in power_nodes)
    dst_is_ground = any(g in dst.upper() for g in ground_nodes)
    
    # If src is power and dst is ground, and net name suggests short, flag it
    if src_is_power and dst_is_ground:
        if any(kw in net.upper() for kw in ("SHORT", "DIRECT", "BYPASS")):
            return True
    
    return False


def _estimate_current(src_comp: Dict, dst_comp: Dict) -> int:
    """
    Heuristic: Estimate current in mA based on component types.
    Real implementation would read from KiCad simulation or design rules.
    """
    src_type = src_comp.get("type", "UNKNOWN")
    dst_type = dst_comp.get("type", "UNKNOWN")
    
    # Power sources → high current
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
    
    # Regulators
    if src_type == "VOLTAGE_REG":
        return 750
    
    # Default
    return 50


# ── CLI for testing ───────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python netlist_parser.py <netlist_file.net>")
        sys.exit(1)
    
    netlist_file = sys.argv[1]
    
    try:
        task = parse_kicad_netlist(netlist_file)
        print(json.dumps(task, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
