import pydantic
from models import Observation, Action, Reward

class MockEnv:
    def __init__(self): pass

class PCBAuditorEnv(MockEnv):
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = {
            "components": {
                "PWR": "9V_Battery",
                "MCU": "IC_3.3V_Sensitive",
                "D1": "LED_Red"
            },
            "connections": [
                ("PWR:VCC", "MCU:VCC"),  # Voltage Mismatch Error
                ("PWR:VCC", "PWR:GND"),  # Short Circuit Error
                ("D1:K", "PWR:GND")
            ]
        }
        self.done = False
        return Observation(
            components=list(self.state["components"].values()),
            netlist=[f"{a} -> {b}" for a, b in self.state["connections"]],
            current_errors=["Initial Scan Required"]
        )

    def _get_connections(self, pin_name):
        return [c for c in self.state["connections"] if pin_name in c[0] or pin_name in c[1]]

    def step(self, action: Action):
        reward = 0.0
        msg = "Audit step completed."

        if action.check_type == "Check_Short_Circuit":
            pwr_pins = self._get_connections("PWR:VCC")
            for conn in pwr_pins:
                if "PWR:GND" in conn[0] or "PWR:GND" in conn[1]:
                    reward = 1.0
                    msg = "Short circuit detected on primary power rail."
                    self.done = True

        elif action.check_type == "Check_Voltage_Mismatch":
            vcc_path = self._get_connections("MCU:VCC")
            for conn in vcc_path:
                if "PWR:VCC" in conn[0] or "PWR:VCC" in conn[1]:
                    if "9V" in self.state["components"]["PWR"]:
                        reward = 1.0
                        msg = "Voltage violation: 9V source connected to 3.3V MCU."
                        self.done = True

        return Observation(
            components=list(self.state["components"].values()),
            netlist=[f"{a} -> {b}" for a, b in self.state["connections"]],
            current_errors=[msg]
        ), Reward(value=reward, message=msg), self.done, {}