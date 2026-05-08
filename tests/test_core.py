import tomllib
import unittest
from pathlib import Path

from environment import Action, PCBAuditorEnv
from netlist_parser import parse_board_file
from tasks import TASKS


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_kicad_parser_respects_explicit_and_inferred_types(self):
        data = parse_board_file(str(ROOT / "boards" / "rfid_system.net"))
        components = {component["id"]: component for component in data["components"]}

        self.assertEqual(components["U1"]["type"], "MICROCONTROLLER")
        self.assertEqual(components["U2"]["type"], "SENSOR_IC")
        self.assertEqual(components["K1"]["type"], "RELAY")
        self.assertEqual(components["B1"]["type"], "POWER_SUPPLY")
        self.assertEqual(components["M1"]["type"], "MOTOR")
        self.assertEqual(components["GND_REF"]["type"], "GROUND")

    def test_parser_chooses_power_source_as_net_driver(self):
        data = parse_board_file(str(ROOT / "boards" / "blind_test_case.net"))
        connections = data["netlist"]

        self.assertIn(
            {"from": "PWR1", "to": "U1", "net": "24V_FATAL_RAIL", "current_ma": 500, "protection": True},
            connections,
        )

    def test_parser_detects_literal_ground_components(self):
        data = parse_board_file(str(ROOT / "boards" / "kicad_syntax_test.net"))
        components = {component["id"]: component for component in data["components"]}

        self.assertEqual(components["GND"]["type"], "GROUND")


class EnvironmentTests(unittest.TestCase):
    def test_declared_task_violations_match_diagnostic_engine(self):
        for task_id, task in TASKS.items():
            with self.subTest(task_id=task_id):
                env = PCBAuditorEnv()
                env.reset(task_id=task_id)
                violations, _ = env._run_all_diagnostics()
                self.assertEqual(set(violations), set(task["violations"]))

    def test_target_nets_filter_diagnostic_edges(self):
        env = PCBAuditorEnv()
        env.reset(task_id="task_full_audit")
        obs, reward, done, info = env.step(
            Action(check_type="check_voltage_mismatch", target_nets=["3V3_RAIL"])
        )

        self.assertIn("No voltage mismatches", obs.last_check_result)
        self.assertEqual(env.state().violations_found, [])
        self.assertFalse(done)

    def test_submit_verdict_rewards_real_findings(self):
        env = PCBAuditorEnv()
        env.reset(task_id="task_full_audit")
        for check in ("check_voltage_mismatch", "check_short_circuit", "check_component_rating"):
            env.step(Action(check_type=check))

        obs, reward, done, info = env.step(
            Action(
                check_type="submit_verdict",
                verdict="24V voltage mismatch, 5V short circuit, and 750mA overcurrent on MCU.",
            )
        )

        self.assertTrue(done)
        self.assertGreaterEqual(info["final_score"], 0.95)
        self.assertGreaterEqual(reward.value, 0.95)

    def test_parsed_sample_boards_do_not_invent_current_faults(self):
        data = parse_board_file(str(ROOT / "boards" / "perfect_board.net"))
        env = PCBAuditorEnv()
        env.reset(custom_task=data)
        violations, _ = env._run_all_diagnostics()

        self.assertEqual(violations, [])

    def test_parsed_blind_board_detects_voltage_mismatch(self):
        data = parse_board_file(str(ROOT / "boards" / "blind_test_case.net"))
        env = PCBAuditorEnv()
        env.reset(custom_task=data)
        violations, _ = env._run_all_diagnostics()

        self.assertIn("VOLTAGE_MISMATCH:PWR1->U1(24.0V>3.6V)", violations)


class ConfigTests(unittest.TestCase):
    def test_server_config_matches_code_entrypoints(self):
        server_source = (ROOT / "server.py").read_text(encoding="utf-8")
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertIn('@app.get("/health"', server_source)
        self.assertIn("def main()", server_source)
        self.assertEqual(pyproject["project"]["scripts"]["server"], "server:main")


if __name__ == "__main__":
    unittest.main()
