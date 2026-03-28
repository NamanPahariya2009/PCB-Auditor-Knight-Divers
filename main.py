import gradio as gr
from inference import your_audit_function

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# ⚡ KNIGHT DIVERS: PCB AUDITOR")
    gr.Markdown("*Advanced Netlist Topology Validation & Risk Assessment*")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ Control Panel")
            task = gr.Radio(
                ["Check_Voltage_Mismatch", "Check_Short_Circuit"], 
                label="Diagnostic Protocol",
                value="Check_Voltage_Mismatch"
            )
            btn = gr.Button("🚀 SCAN PCB NETLIST", variant="primary")
            
        with gr.Column(scale=2):
            gr.Markdown("### 🖥️ Diagnostic Visualization")
            visualizer = gr.Plot(label="Netlist Topology Map")
            output_text = gr.Markdown("### 📡 WAITING FOR INPUT...")

    btn.click(
        fn=your_audit_function, 
        inputs=task, 
        outputs=[output_text, visualizer]
    )

if __name__ == "__main__":
    demo.launch()