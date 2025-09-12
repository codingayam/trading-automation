# Triage Report: Railway Scheduler Process Crash

## Summary
- **Symptom:** Scheduler process repeatedly exits with status 1 immediately after startup, while dashboard runs successfully
- **Scope/Blast Radius:** Railway deployment only - scheduler process fails, dashboard works fine
- **First Seen / Last Known Good:** Latest commit 016b843 (Sep 12, 2025) - removed simple_scheduler.py but supervisord.conf still references it
- **Environments Affected:** Railway production deployment
- **Related Tickets/Deploys/Flags:** Commit 016b843 "Complete codebase cleanup" removed 6 scheduler files including simple_scheduler.py

## Likely Components & Paths
- **Process Management** → supervisord.conf pointing to non-existent file
- **Railway Deployment** → Configuration mismatch between cleanup and supervisor config
- **Candidate paths:**
  - `/Users/admin/github/trading-automation/deployment/railway/supervisord.conf` (PRIMARY)
  - `/Users/admin/github/trading-automation/main.py` (scheduler command handling)
  - `/Users/admin/github/trading-automation/config/settings.py` (environment loading)

## Ranked Hypotheses

1) **Missing simple_scheduler.py file** — Confidence: 95
   - **Mechanism:** supervisord.conf still references `python3 simple_scheduler.py` but commit 016b843 deleted the file
   - **Evidence for:** 
     - Commit 85b64e1 changed supervisord to use `python3 simple_scheduler.py`
     - Commit 016b843 deleted simple_scheduler.py but didn't update supervisord.conf
     - Exit status 1 = file not found / command failed to start
     - Dashboard works fine (uses railway_dashboard.py which exists)
   - **Evidence against:** None - this is clearly the root cause
   - **Quick validation:** Check if simple_scheduler.py exists in Railway container
   - **Expected observation if true:** "python3: can't open file 'simple_scheduler.py'" error in scheduler logs

2) **supervisord.conf not updated after cleanup** — Confidence: 90
   - **Mechanism:** Configuration file wasn't synced with code cleanup in commit 016b843
   - **Evidence for:** 
     - Current supervisord.conf line 8: `command=python3 simple_scheduler.py`  
     - Should be: `command=python3 main.py start` (unified command)
     - Cleanup removed 6 files but missed updating supervisord config
   - **Evidence against:** None
   - **Quick validation:** Compare supervisord.conf in current deploy vs. what should be there
   - **Expected observation if true:** Scheduler will start working after fixing the command

3) **Railway deployment using wrong supervisord.conf** — Confidence: 75
   - **Mechanism:** Railway might be using cached/old version of supervisord.conf
   - **Evidence for:** 
     - Recent commits show Railway deployment issues being debugged
     - Multiple scheduler variants were tested (simple_scheduler, debug_scheduler, etc.)
   - **Evidence against:** Dashboard is working, so Railway is using current code
   - **Quick validation:** Check Railway logs for actual command being executed
   - **Expected observation if true:** Old supervisord.conf being used despite code changes

4) **Environment variable issues** — Confidence: 25
   - **Mechanism:** Missing API keys causing immediate scheduler exit
   - **Evidence for:** Exit status 1 could indicate environment validation failure
   - **Evidence against:** 
     - Dashboard is working fine (would also need same env vars)
     - Simple_scheduler.py had retry logic for missing env vars, not immediate exit
   - **Quick validation:** Check Railway environment variables are set
   - **Expected observation if true:** "Missing environment variables" in logs

## High-Signal Checks (Do First)
- [ ] **Check Railway logs for exact error message** - Look for "can't open file" or "No such file" 
- [ ] **Verify supervisord.conf command in Railway deployment** - Should be `python3 main.py start` not `python3 simple_scheduler.py`
- [ ] **Confirm simple_scheduler.py doesn't exist in Railway container** - File should be deleted per commit 016b843
- [ ] **Test scheduler command locally** - Run `python3 main.py start` to ensure it works

## Recent Changes (last 20 commits touching suspects)
- **016b843** — deployment/railway/supervisord.conf — Complete codebase cleanup (deleted simple_scheduler.py) — Sep 12, 2025
- **85b64e1** — deployment/railway/supervisord.conf — Changed to use simple_scheduler.py — Sep 11, 2025  
- **954e283** — deployment/railway/supervisord.conf — Fix supervisor config for exit codes — (recent)
- **ebd9bab** — (Railway diagnostic) — Add diagnostic test for crash root cause — (recent)
- **cc793ae** — (Railway debugging) — Improve error logging — (recent)

## Data Gaps & Requests
- **Need:** Full Railway scheduler.log content showing actual Python error
- **Need:** Railway container file listing to confirm simple_scheduler.py is missing  
- **Need:** Current supervisord.conf as deployed to Railway (may differ from git)
- **Need:** Railway build logs to see if deployment picked up latest supervisord.conf changes

## Handoff to Debugger subagent
- **Start with:** `/Users/admin/github/trading-automation/deployment/railway/supervisord.conf`
- **Try to falsify Hypothesis #1** via updating line 8 from `command=python3 simple_scheduler.py` to `command=python3 main.py start`
- **Expected result:** Scheduler should start successfully and remain running
- **If falsified:** Check Hypothesis #3 (Railway using cached config) or #4 (environment issues)
- **If confirmed:** Deploy the supervisord.conf fix to Railway and monitor for successful startup

**Critical insight:** This is a classic "left hand doesn't know what right hand did" scenario where code cleanup removed a file but didn't update the configuration that references it. The fix should be straightforward once the supervisord.conf command is corrected.