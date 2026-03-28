import gradio as gr
from inference import your_audit_function

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# ⚡ KNIGHT DIVERS: PCB AUDITOR")
    with gr.Row():
        with gr.Column(scale=1):
            task = gr.Radio(["Check_Voltage_Mismatch", "Check_Short_Circuit"], label="Diagnostic Protocol")
            btn = gr.Button("🚀 SCAN PCB NETLIST", variant="primary")
        with gr.Column(scale=2):
            visualizer = gr.Plot(label="Netlist Topology Map")
            output_text = gr.Markdown("### 📡 WAITING FOR SCAN...")
    btn.click(fn=your_audit_function, inputs=task, outputs=[output_text, visualizer])

if __name__ == "__main__":
    demo.launch()