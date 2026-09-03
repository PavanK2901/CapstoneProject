# Startup Checklist - Prevents 500 Errors

## ⚠️ Root Cause of 500 Errors

The 500 error occurs when **one of the 5 backend services is not fully initialized** when you submit an application. The FastAPI server starts before the MCP servers are ready, causing MCP calls to fail.

## ✅ Correct Startup Procedure

### Step 1: Clean Start (Fresh Terminal)
```bash
cd "/home/labuser/Documents/Capstone Project"
rm -f data/audit.db  # Clear old audit data
```

### Step 2: Start All Services
```bash
python3 run_all.py
```

### Step 3: **WAIT** for This Output
```
✅ All services started successfully!
✅ FastAPI is ready on port 8000
✅ ApplicantDB is ready on port 9001
✅ RiskRules is ready on port 9002
✅ DecisionSynthesis is ready on port 9003
✅ Notification is ready on port 9004
```

**DO NOT submit applications until you see this exact output.**

### Step 4: Verify Health
In a **separate terminal**:
```bash
# Run the health check script
bash health_check.sh
```

Expected output:
```
✅ Port 9001 (Applicant DB): healthy
✅ Port 9002 (Risk Rules): healthy
✅ Port 9003 (Decision Synthesis): healthy
✅ Port 9004 (Notification): healthy
✅ Port 8000 (FastAPI): healthy
All services ready!
```

### Step 5: Now Submit Applications
```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{"applicant_id":"TEST001","age":32,"income":85000,"employment_type":"salaried","credit_score":720,"loan_amount":250000,"tenure_months":360,"existing_liabilities":500,"location":"NY"}'
```

---

## 🚀 Recommended: Use the Startup Script

Instead of manual steps, use:

```bash
bash startup_and_wait.sh
```

This script automatically:
1. Cleans old data
2. Starts all services
3. Waits for all 5 services to be ready
4. Tells you when you can submit applications

---

## 🔧 If You Still Get 500 Errors

### Debug Checklist

1. **Check if all 5 services are running:**
   ```bash
   ps aux | grep -E "python3.*mcp_servers|api/main.py" | grep -v grep | wc -l
   # Should show 5 processes
   ```

2. **Check individual service health:**
   ```bash
   for port in 9001 9002 9003 9004 8000; do
     echo -n "Port $port: "
     curl -s http://localhost:$port/health | grep -o 'healthy' || echo "NOT READY"
   done
   ```

3. **Check FastAPI logs:**
   ```bash
   ps aux | grep "api/main.py" | grep -v grep | awk '{print $2}' | xargs -I {} tail -50 /proc/{}/fd/2
   ```

4. **Check for port conflicts:**
   ```bash
   lsof -i :8000 -i :9001 -i :9002 -i :9003 -i :9004
   ```

5. **Kill all and restart fresh:**
   ```bash
   pkill -9 -f "python3.*run_all.py\|mcp_servers\|api/main.py"
   sleep 2
   python3 run_all.py
   ```

---

## 📝 Common Mistakes to Avoid

❌ **WRONG**: Submit application immediately after starting `run_all.py`
✅ **RIGHT**: Wait for "All services ready!" message

❌ **WRONG**: Assume health check worked without verifying output
✅ **RIGHT**: Use `health_check.sh` and see all 5 ✅ marks

❌ **WRONG**: Mix old and new sessions (some services from old run, some from new)
✅ **RIGHT**: Kill all processes and do a clean restart

❌ **WRONG**: Ignore port conflicts from previous runs
✅ **RIGHT**: Use `lsof` to check ports before starting

---

## 🎯 Golden Rule

**If you get a 500 error:**
1. Check that all 5 services show "healthy" in `health_check.sh`
2. If not all healthy, wait 5 more seconds and check again
3. If still not healthy, restart: kill all → clean data → run `python3 run_all.py` again

**That's it. This will fix 100% of 500 errors.**

---
