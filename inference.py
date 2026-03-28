import gradio as gr
from main import PCBAuditorEnv
from models import Action

def run_pcb_audit(check_type):
    # Initialize the Knight Divers environment
    env = PCBAuditorEnv()
    env.reset()
    
    # Execute the selected audit task
    act = Action(check_type=check_type, target="All")
    obs, reward, done, info = env.step(act)
    
    # Format the results for the UI
    status_emoji = "🚨 VIOLATION FOUND" if reward.value > 0 else "✅ SYSTEM CLEAR"
    
    result_md = f"## {status_emoji}\n"
    result_md += f"**Audit Message:** {reward.message}\n\n"
    result_md += f"**Components Scanned:** {', '.join(obs.components)}\n\n"
    result_md += f"**Reward Score:** {reward.value}\n"
    
    return result_md

# Stark Lab UI Layout
with gr.Blocks(title="Knight Divers: PCB Auditor") as demo:
    gr.Markdown("# ⚡ Knight Divers: Industrial PCB Auditor")
    gr.Markdown("Real-time graph-based netlist validation for the April 8th Hackathon.")
    
    with gr.Row():
        with gr.Column():
            check_selector = gr.Radio(
                ["Check_Voltage_Mismatch", "Check_Short_Circuit"], 
                label="Select Security Protocol", 
                value="Check_Voltage_Mismatch"
            )
            run_btn = gr.Button("Execute Audit Scan", variant="primary")
        
        with gr.Column():
            output_display = gr.Markdown("### Diagnostic Results\nWaiting for scan...")
    
    # Logic trigger
    run_btn.click(fn=run_pcb_audit, inputs=check_selector, outputs=output_display)

if __name__ == "__main__":
    # Port 7860 is required for Hugging Face Spaces
    demo.launch(server_port=7860)