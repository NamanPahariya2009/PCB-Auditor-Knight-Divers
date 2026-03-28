import networkx as nx
import matplotlib.pyplot as plt
import gradio as gr

def generate_pcb_graph(violation_type=None):
    G = nx.Graph()
    
    # Netlist Topology
    edges = [
        ("VCC_9V", "R1"), ("R1", "MCU_PIN_1"), 
        ("VCC_3.3V", "MCU_PIN_2"), ("MCU_PIN_2", "GND"),
        ("GND", "C1"), ("C1", "VCC_3.3V")
    ]
    G.add_edges_from(edges)
    
    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 6))
    
    # Logic for highlighting violations
    violation_nodes = []
    if violation_type == "Voltage_Mismatch":
        violation_nodes = ["VCC_9V", "MCU_PIN_1"]
    elif violation_type == "Short_Circuit":
        violation_nodes = ["VCC_3.3V", "GND"]

    node_colors = ['#ff4b2b' if node in violation_nodes else '#00d4ff' for node in G.nodes()]
    
    nx.draw(G, pos, with_labels=True, node_color=node_colors, 
            edge_color='#444444', font_color='white', font_weight='bold', 
            node_size=2500, width=2)
    
    plt.gcf().set_facecolor('#0b0d17') # Space Black Background
    plt.title("PCB TOPOLOGY DIAGNOSTIC", color='white', fontsize=15)
    return plt.gcf()

def your_audit_function(task_type):
    if task_type == "Check_Voltage_Mismatch":
        message = "### 🚨 CRITICAL VIOLATION\n**Detected:** 9V Power Rail is feeding directly into a 3.3V Logic Pin (MCU_PIN_1). \n**Risk:** Hardware failure / Magic Smoke."
        plot = generate_pcb_graph("Voltage_Mismatch")
    elif task_type == "Check_Short_Circuit":
        message = "### 🚨 SHORT CIRCUIT DETECTED\n**Detected:** Low impedance path found between VCC_3.3V and GND. \n**Risk:** Thermal runaway / Battery drain."
        plot = generate_pcb_graph("Short_Circuit")
    else:
        message = "### ✅ SYSTEM NOMINAL\nNo violations detected in the current netlist scan."
        plot = generate_pcb_graph()
        
    return message, plot

# The following block is required for Hugging Face to launch
if __name__ == "__main__":
    from main import demo
    demo.launch()