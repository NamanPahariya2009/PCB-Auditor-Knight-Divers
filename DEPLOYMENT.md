# PCB Auditor — Deployment Checklist (April 7th)
# Knight Divers | Naman Pahariya & Kapish Gupta

## Files to Deploy

Updated files (replace existing):
- ✅ server.py          (adds .net upload tab)
- ✅ README.md          (documents 4th task + .net parsing)
- ✅ environment.py     (same as v2)
- ✅ tasks.py           (has all 4 tasks including task_industrial_mcu)
- ✅ inference.py       (same baseline)
- ✅ requirements.txt   (same deps)
- ✅ Dockerfile         (same)
- ✅ openenv.yaml       (same spec)

New files (add):
- ✅ netlist_parser.py  (KiCad .net file parser)
- ✅ sample_board.net   (example netlist for testing)

## Git Deployment Commands

```bash
# Navigate to your repo
cd PCB-Auditor-Knight-Divers

# Copy all files from /mnt/user-data/outputs/
# (download them from Claude.ai first)

# Add new parser
git add netlist_parser.py sample_board.net

# Update existing files
git add server.py README.md environment.py tasks.py inference.py
git add requirements.txt Dockerfile openenv.yaml

# Commit
git commit -m "v3: Add KiCad .net parser + 4th expert task + baseline 1.00 scores"

# Push to GitHub (triggers HF Space auto-rebuild)
git push origin main
```

## Post-Deploy Verification

1. **Wait 2-3 minutes** for HF Space to rebuild

2. **Test endpoints:**
   ```bash
   curl https://jarvis217-pcb-auditor-knight-divers.hf.space/health
   # Should return: {"status":"online","environment":"PCB Auditor Knight Divers"}
   
   curl https://jarvis217-pcb-auditor-knight-divers.hf.space/tasks
   # Should list 4 tasks including task_industrial_mcu
   ```

3. **Test Gradio HUD:**
   - Open https://huggingface.co/spaces/Jarvis217/PCB-Auditor-Knight-Divers
   - Check "Upload .net File" tab exists
   - Upload sample_board.net
   - Run check_voltage_mismatch
   - Verify graph shows VCC→U1 edge in Safety Orange
   - Verdict should detect 9V→3.6V mismatch

4. **Run baseline inference** (locally first to verify):
   ```bash
   export OPENROUTER_API_KEY=your-key-here
   export MODEL_NAME=google/gemini-3-flash-preview
   python inference.py
   ```
   - Should output 4 tasks with avg score 1.00
   - Results saved to baseline_results.json

## Success Criteria

✅ `/health` returns 200 OK
✅ `/tasks` lists 4 tasks
✅ Gradio shows 3 tabs: Built-in | JSON | Upload .net
✅ .net file upload works without errors
✅ Parser extracts components correctly
✅ Graph highlights violation paths in orange
✅ Baseline achieves 1.00 average on all 4 tasks

## Rollback Plan (if needed)

```bash
git revert HEAD
git push origin main
```

---

## What Changed (Upgrade Summary)

### v2 → v3 Upgrades:
1. **KiCad .net Parser** (`netlist_parser.py`)
   - Parses S-expression format
   - Extracts components + netlist connections
   - Infer types heuristically (MCU, regulator, etc.)
   - Integrates via Gradio upload tab

2. **4th Expert Task** (`task_industrial_mcu`)
   - Tests `check_missing_decoupling` heuristic
   - 3 violations: voltage + overcurrent + missing capacitor
   - Baseline achieves 1.00 score

3. **Baseline Model Swap**
   - Old: google/gemma-3-27b-it (avg 0.75)
   - New: google/gemini-3-flash-preview (avg 1.00)

4. **README Updates**
   - Documents .net upload workflow
   - Shows 4 tasks instead of 3
   - Updated baseline scores table

### No Breaking Changes:
- All OpenEnv API endpoints unchanged
- Built-in tasks still work exactly the same
- JSON Live Fire still works
- Docker deployment unchanged
