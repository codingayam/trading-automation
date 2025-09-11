# Triage Report: Dashboard Port 5000 Accessibility Issue

## Summary
- **Symptom:** Dashboard Flask app not accessible via browser despite appearing to run successfully
- **Scope/Blast Radius:** Dashboard web interface only - trading system (Andy Grok Agent) working perfectly
- **First Seen / Last Known Good:** Recent issue - multiple dashboard processes started simultaneously
- **Environments Affected:** Local development environment (macOS Darwin 24.6.0)
- **Related Tickets/Deploys/Flags:** Multiple background dashboard processes running concurrently

## Likely Components & Paths
- **Primary Subsystem:** Dashboard web interface → Flask app binding/port conflict issue
- **Secondary Subsystem:** Process management → Multiple instance conflict
- **Candidate paths:**
  - `/Users/admin/github/trading-automation/src/dashboard/run_dashboard.py` (main entry point)
  - `/Users/admin/github/trading-automation/src/dashboard/api.py` (Flask app configuration)
  - `/Users/admin/github/trading-automation/config/settings.py` (dashboard configuration)

## Ranked Hypotheses

1) **Apple AirTunes Service Port Hijacking** — Confidence: 95
   - **Mechanism:** macOS AirTunes/AirPlay service (ControlCenter process PID 1313) has bound to port 5000, preventing Flask from binding properly
   - **Evidence for:** 
     - lsof shows ControlCenter (Apple service) listening on port 5000
     - curl returns `403 Forbidden` with AirTunes server header
     - Multiple dashboard processes show startup messages but can't actually bind to port
   - **Evidence against:** None - this is a classic macOS development issue
   - **Quick validation:** Check `lsof -i :5000` output showing ControlCenter process
   - **Expected observation if true:** Flask processes start but can't bind to port, Apple service responds instead

2) **Flask Debug Mode Auto-Restart Loop** — Confidence: 85
   - **Mechanism:** Flask's debug mode with `use_reloader=True` creating multiple processes, but port already taken by system service
   - **Evidence for:**
     - Multiple "Dashboard started" messages in logs
     - Debug mode enabled in settings (`debug=True`)
     - Flask reloader warnings in stderr logs
   - **Evidence against:** Would typically show port binding errors more clearly
   - **Quick validation:** Check for reloader-specific error messages or child processes
   - **Expected observation if true:** Multiple Flask processes attempting to start, with child processes failing silently

3) **Dashboard Configuration Host/Port Binding Issue** — Confidence: 60
   - **Mechanism:** Flask app not binding to correct interface or conflicting with system services
   - **Evidence for:**
     - App claims to start on 127.0.0.1:5000 but system service owns the port
     - No clear Flask startup success message about actual binding
   - **Evidence against:** Configuration appears correct in logs
   - **Quick validation:** Try different port in settings or check actual Flask binding status
   - **Expected observation if true:** Flask would report successful start but actually fail to bind

4) **Health Check Endpoint Errors** — Confidence: 40
   - **Mechanism:** Health endpoint throwing exceptions preventing proper Flask response handling
   - **Evidence for:**
     - Multiple "Unexpected error in health_check: 'overall_status'" in logs
     - API endpoints returning empty responses
   - **Evidence against:** This is likely a symptom, not the root cause of port access
   - **Quick validation:** Check health check implementation for dictionary key errors
   - **Expected observation if true:** Health endpoint would work once port conflict resolved

## High-Signal Checks (Do First)

- [ ] **Verify port ownership:** `lsof -i :5000` - Confirm Apple AirTunes is using port 5000
- [ ] **Check alternative port:** Modify dashboard settings to use port 5001 or 8080 and test access
- [ ] **Disable AirPlay receiver:** System Preferences > Sharing > AirPlay Receiver (disable temporarily)
- [ ] **Test direct Flask binding:** Try running Flask on different port to isolate the issue

## Recent Changes (last 20 commits touching suspects)
- Could not analyze git log due to focus on immediate port conflict resolution
- Multiple background processes were started recently causing the conflict scenario

## Data Gaps & Requests
- **Need:** Current dashboard configuration values from settings object
- **Need:** Exact Flask binding attempt logs (not just startup messages) 
- **Need:** System service configuration for port 5000 usage
- **Need:** Clear process tree showing parent/child Flask relationships

## Handoff to Debugger subagent
- **Start with:** `/Users/admin/github/trading-automation/config/settings.py` - Change dashboard port from 5000 to 5001
- **Try to falsify Hypothesis #1:** Kill all existing dashboard processes, change port to 5001, start single dashboard instance
- **If falsified:** Check Hypothesis #2 by disabling Flask debug mode and reloader
- **Expected outcome:** Dashboard should be accessible on alternate port, confirming Apple AirTunes port conflict

## Key Technical Details
- **Port Conflict Evidence:** ControlCenter (PID 1313) owns port 5000
- **HTTP Response:** `403 Forbidden` with `Server: AirTunes/870.14.1` header
- **Process State:** Multiple dashboard background processes killed/terminated
- **Core Issue:** System service priority over user applications for well-known ports

## Immediate Resolution Path
1. Change dashboard port from 5000 to 5001 in configuration
2. Kill any remaining dashboard processes
3. Start single dashboard instance on new port
4. Test browser access to confirm resolution