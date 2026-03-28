import gradio as gr
from main import PCBAuditorEnv
from models import Action

def run_pcb_audit(check_type):
    env = PCBAuditorEnv()
    env.reset()
    act = Action(check_type=check_type, target="All")
    obs, reward, done, info = env.step(act)
    
    status = "🚨 VIOLATION" if reward.value > 0 else "✅ CLEAR"
    return f"### {status}\n**Result:** {reward.message}\n**Score:** {reward.value}"

# The UI that stays alive forever
with gr.Blocks(title="Knight Divers Auditor") as demo:
    gr.Markdown("# ⚡ Knight Divers: PCB Auditor")
    with gr.Row():
        check_selector = gr.Radio(["Check_Voltage_Mismatch", "Check_Short_Circuit"], label="Select Task")
        run_btn = gr.Button("Scan PCB", variant="primary")
    output = gr.Markdown("Waiting for scan...")
    run_btn.click(fn=run_pcb_audit, inputs=check_selector, outputs=output)

if __name__ == "__main__":
    # This server_port 7860 is the key to staying "Green"
    demo.launch(server_port=7860)