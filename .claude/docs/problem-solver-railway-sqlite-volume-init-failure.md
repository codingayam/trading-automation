# Triage Report: Railway SQLite Database Initialization Failure with Volume Mount

## Summary
- **Symptom:** Database initialization fails silently after adding Railway persistent volume for SQLite
- **Scope/Blast Radius:** Complete system failure - no agents initialized, dashboard non-functional
- **First Seen:** After adding Railway volume mount configuration
- **Last Known Good:** Before volume mount - ephemeral SQLite at `data/trading_automation.db` worked fine
- **Environments Affected:** Railway production deployment only
- **Related Changes:** Addition of Railway volume mount at `/app/data` with `DATABASE_PATH=/app/data/trading_automation.db`

## Likely Components & Paths
- **Database Layer** → SQLite file creation/initialization failing on mounted volume
- **File System Permissions** → Railway volume permissions vs container user permissions
- **Path Resolution** → Directory creation and file access patterns
- **Container Initialization** → Dockerfile and supervisord startup sequence

**Candidate paths:**
- `src/data/database.py` - Database initialization logic
- `initialize_agents.py` - Agent initialization orchestration
- `Dockerfile.railway` - Container setup and user permissions
- `deployment/railway/supervisord.conf` - Process startup order

## Ranked Hypotheses

1) **File System Permissions Mismatch** — Confidence: 90
   - **Mechanism:** Railway volume mount has different ownership/permissions than container user (`tradingapp`). DatabaseManager's `Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)` fails due to permission denied on `/app/data`.
   - **Evidence for:** Container runs as `tradingapp` user, Railway volumes often mount with root ownership, Dockerfile creates `/app/data` but volume may override permissions
   - **Evidence against:** Volume mount log shows successful mounting, but this doesn't verify write permissions
   - **Quick validation:** Check directory permissions and ownership in `/app/data`, test file creation manually
   - **Expected observation if true:** `PermissionError` during directory creation or SQLite file creation in `database.py:44`

2) **Silent Exception Handling in Initialize Flow** — Confidence: 85
   - **Mechanism:** `initialize_agents.py:26` checks `if not initialize_database():` but `initialize_database()` catches ALL exceptions and returns `False`, masking the real error. The actual error is logged but not printed to stdout.
   - **Evidence for:** `database.py:384-386` has broad exception handling, logs error but returns False. `initialize_agents.py` prints generic message but continues execution.
   - **Evidence against:** Logging should capture the real error
   - **Quick validation:** Add explicit error printing in initialization or check Railway logs for detailed error messages
   - **Expected observation if true:** Real error is in logs but not visible in Railway deployment output

3) **Container User vs Volume Mount Ownership** — Confidence: 80
   - **Mechanism:** Dockerfile creates `/app/data` as `tradingapp:tradingapp` but Railway volume mounts over this with different ownership (likely `root:root`), preventing writes.
   - **Evidence for:** Line 36-37 in Dockerfile creates directory and changes ownership, but volume mount can override this
   - **Evidence against:** Railway documentation suggests volumes should inherit container permissions
   - **Quick validation:** Compare `ls -la /app/data` before and after volume mount in container
   - **Expected observation if true:** `/app/data` exists but owned by root, not tradingapp

4) **Path Resolution Issue in DATABASE_PATH** — Confidence: 60
   - **Mechanism:** `settings.py:28-30` resolves paths using `PROJECT_ROOT`, but with absolute path `/app/data/trading_automation.db`, the path resolution logic may not work as expected in container context.
   - **Evidence for:** `full_path` property logic assumes relative vs absolute paths, container environment different from dev
   - **Evidence against:** `os.path.isabs()` should properly detect absolute paths
   - **Quick validation:** Log actual resolved database path during initialization
   - **Expected observation if true:** Database path resolves incorrectly, file created in wrong location

## High-Signal Checks (Do First)
- [ ] **Expose the real error:** Modify `initialize_agents.py` to print the actual exception from `initialize_database()` instead of generic failure message
- [ ] **Check volume mount permissions:** Use Railway exec to run `ls -la /app/data` and `whoami` to verify ownership and writability
- [ ] **Test manual file creation:** In Railway container, try `touch /app/data/test.txt` as `tradingapp` user to verify write permissions
- [ ] **Add debug logging:** Instrument `database.py:44` and `database.py:374` with specific path and permission logging

## Recent Changes (last 20 commits touching suspects)
- **Volume mount addition** - Railway configuration change (not in git history)
- **DATABASE_PATH environment variable** - Changed from `data/trading_automation.db` to `/app/data/trading_automation.db`
- **Container permissions** - May have changed with volume mount behavior

## Data Gaps & Requests
- **Need:** Exact error message from database initialization (currently silent failure)
- **Need:** Directory listing and permissions of `/app/data` inside Railway container
- **Need:** Full stack trace from database.py initialization failure
- **Need:** Verification that environment variables are accessible to initialization script
- **Need:** Railway container filesystem layout during startup

## Handoff to Debugger subagent
- **Start with:** `/Users/admin/github/trading-automation/initialize_agents.py` lines 26-29 - modify error handling to expose real database initialization error
- **Primary target:** Add exception printing in `initialize_agents.py:28` to capture the actual error from `initialize_database()` 
- **Secondary target:** `/Users/admin/github/trading-automation/src/data/database.py` lines 384-386 - enhance error logging with filesystem details
- **Try to falsify Hypothesis #1 via:** Check if error message reveals permission denied on `/app/data` directory creation
- **If falsified, proceed to #2:** Focus on the Railway logs to find the masked error details

**Immediate Action Required:**
1. **Modify** `initialize_agents.py` to print caught exceptions instead of generic "Database initialization failed"  
2. **Test deployment** with enhanced error reporting to see actual failure cause
3. **If permissions issue confirmed:** Fix container user ownership or Railway volume configuration
4. **If different issue:** Use revealed error message to identify specific root cause

**Files to modify first:**
- `/Users/admin/github/trading-automation/initialize_agents.py` (lines 26-29)
- `/Users/admin/github/trading-automation/src/data/database.py` (lines 384-386)