# Triage Report: Obsolete Code After Unified Market Hours Implementation

## Summary
- **Symptom**: After implementing unified market hours execution (all agents at 9:30 AM ET), multiple files and code sections remain from the old 9:30 PM EST congressional-only scheduling approach
- **Scope/Blast Radius**: Affects deployment files, Railway scripts, systemd services, documentation, and configuration settings
- **First Seen / Last Known Good**: Change implemented recently with market hours unification
- **Environments Affected**: Development, Railway deployment, production deployment
- **Related Changes**: Implementation of `python3 main.py start` command and unified `intraday_scheduler.py` handling both congressional and technical agents

## Likely Components & Paths
- **Railway Deployment Scripts** → Legacy deployment files for old 9:30 PM scheduling
- **Systemd Services** → Separate services for congressional vs technical agents (now unified)
- **Root Directory Scheduler Scripts** → Debug and alternative scheduler implementations
- **Documentation Files** → References to old 9:30 PM execution model
- **Configuration** → Legacy scheduling settings and references

### Candidate paths:
- `/railway_*.py` - Railway-specific scheduler scripts
- `/simple_scheduler.py` - Simplified scheduler implementation
- `/debug_scheduler.py` - Debug scheduler for Railway issues  
- `/deployment/systemd/` - Separate systemd services
- Various markdown documentation files

## Ranked Hypotheses

### 1) Railway Deployment Scripts are Obsolete — Confidence: 95
- **Mechanism**: These files implement separate scheduler approaches that predate the unified market hours system
- **Evidence for**: Files like `railway_scheduler.py`, `railway_simple.py`, `simple_scheduler.py` contain hardcoded 21:30 execution logic and old scheduler imports
- **Evidence against**: May still be needed for Railway-specific error handling or debugging
- **Quick validation**: Check if Railway deployment now uses `python3 main.py start` vs these custom scripts
- **Expected observation if true**: Railway deployment files contain references to old `daily_runner` and 9:30 PM execution

### 2) Systemd Services Should be Consolidated — Confidence: 90
- **Mechanism**: Separate systemd services for congressional and technical agents are no longer needed with unified scheduler
- **Evidence for**: `trading-scheduler.service` runs `main.py scheduler` and `trading-intraday.service` runs `main.py intraday`, but unified approach uses `main.py start`
- **Evidence against**: May want to keep separate services for resource isolation or separate restart policies
- **Quick validation**: Check if production deployment should use single unified service
- **Expected observation if true**: Two separate services when one unified service would suffice

### 3) Legacy Configuration Settings are Unused — Confidence: 85
- **Mechanism**: Settings for 9:30 PM execution (21:30) are no longer relevant with market hours execution
- **Evidence for**: `settings.py` contains `daily_execution_time = 21:30` which conflicts with market hours model
- **Evidence against**: Settings may still be used by `main.py scheduler` command (old path)
- **Quick validation**: Check if `daily_execution_time` setting is referenced in unified workflow
- **Expected observation if true**: 21:30 execution time setting is referenced but not used in unified flow

### 4) Documentation Contains Stale Information — Confidence: 80
- **Mechanism**: Various markdown files reference the old 9:30 PM execution model
- **Evidence for**: Multiple files found containing "21:30" and "9:30 PM" references
- **Evidence against**: Some references may be historical context or alternative usage documentation
- **Quick validation**: Search for outdated execution time references in user-facing documentation
- **Expected observation if true**: Documentation inconsistency between old evening execution and new market hours execution

## High-Signal Checks (Do First)
- [ ] **Check Railway deployment configuration**: Verify if Railway is now using `python3 main.py start` or still using legacy `railway_scheduler.py`
- [ ] **Audit main.py command usage**: Confirm which commands are actually used in production (`start` vs `scheduler` + `intraday`)
- [ ] **Review systemd service consolidation**: Determine if production needs unified service or separate services
- [ ] **Search codebase for 21:30 references**: Identify all hardcoded 9:30 PM execution references that may be obsolete

## Recent Changes (last 20 commits touching suspects)
Based on the git status and recent commits focusing on Railway scheduler fixes, these files were recently modified for Railway deployment issues but may now be obsolete:

- `railway_scheduler.py` - Railway-specific scheduler with old daily_runner import
- `simple_scheduler.py` - Ultra-simple scheduler with hardcoded 21:30 logic
- `debug_scheduler.py` - Debug scheduler for troubleshooting Railway deployment
- `deployment/systemd/trading-scheduler.service` - Systemd service for congressional agents only
- `deployment/systemd/trading-intraday.service` - Systemd service for technical agents only

## Data Gaps & Requests
- **Need**: Current Railway deployment configuration to confirm which entry point is used
- **Need**: Production systemd service configuration to determine consolidation approach  
- **Need**: Usage analytics on `main.py` commands to identify which are actually used
- **Need**: Dependencies check to see if any external systems reference the legacy scheduler files

## Handoff to Debugger subagent

**Start with**: Review the actual Railway deployment configuration and production deployment scripts to confirm current entry points

**Try to falsify Hypothesis #1** via checking if Railway deployment configuration uses the legacy `railway_scheduler.py` or `simple_scheduler.py` files, or if it has been updated to use the unified `python3 main.py start` command.

**If falsified**, proceed to Hypothesis #2 (systemd service consolidation); otherwise continue analyzing the Railway files and their dependency chain.

**Priority file analysis order**:
1. Railway deployment configuration (`railway.json`, Railway service configuration)
2. `railway_scheduler.py`, `railway_simple.py`, `simple_scheduler.py` - assess if still needed
3. `deployment/systemd/` services - evaluate consolidation opportunities  
4. Documentation files - update references to unified market hours approach
5. Configuration settings - remove unused 9:30 PM execution parameters

---

## Files to DELETE

### High Confidence (Recommend Deletion)

#### Railway Debug/Alternative Scripts
- **`/simple_scheduler.py`** - Contains hardcoded 21:30 logic that conflicts with unified approach
- **`/debug_scheduler.py`** - Debugging tool specific to old scheduler startup issues
- **`/railway_simple.py`** - Alternative Railway implementation for old scheduling model

#### Test/Temporary Files  
- **`/test_agent_system.py`** - If this is a temporary testing script not part of the main test suite

### Medium Confidence (Investigate Then Delete)

#### Railway Deployment Scripts
- **`/railway_scheduler.py`** - Railway-specific scheduler that may be replaced by unified approach
- **`/railway_debug.py`** - Another Railway debugging tool that may be obsolete

Note: Keep `railway_dashboard.py` and `railway_test.py` as they serve different purposes.

## Files to MODIFY

### Configuration Files

#### `/config/settings.py`
**Sections to review/modify**:
- **Line 131**: `daily_execution_time=os.getenv('DAILY_EXECUTION_TIME', '21:30')` - This 21:30 default may be obsolete if unified scheduler doesn't use it
- **Lines 133-134**: Market hours settings may need to be primary timing mechanism
- **Consider**: Adding deprecation warnings for evening execution settings

#### `/main.py` 
**Sections to review**:
- **Lines 482, 516-517**: `scheduler` and `intraday` commands - assess if these should be deprecated in favor of unified `start` command
- **Line 79**: `daily_execution_time` setting reference in scheduler function
- **Consider**: Adding deprecation notices for separate scheduler commands

### Systemd Service Files

#### `/deployment/systemd/trading-scheduler.service`
**Sections to modify**:
- **Line 17**: `ExecStart=/path/to/trading-automation/venv/bin/python main.py scheduler` - Should this be `main.py start`?
- **Lines 1-2**: Description mentions "Congressional Trades" only - update for unified approach

#### `/deployment/systemd/trading-intraday.service`  
**Sections to modify**:
- **Line 17**: `ExecStart=/path/to/trading-automation/venv/bin/python main.py intraday` - Should this be consolidated?
- **Lines 1-2**: Description mentions "Andy Grok Agent" only - assess if separate service needed

### Documentation Files

#### `/CLAUDE.md`
**Sections to update**:
- **Lines referencing 21:30/9:30 PM**: Update to reflect market hours execution
- **Scheduler command examples**: Update to prioritize `python3 main.py start`
- **Architecture diagrams**: Update timing references

#### Railway Documentation Files
- **`/RAILWAY_DEPLOYMENT.md`** - Update deployment procedures
- **`/RAILWAY_SETUP.md`** - Update setup instructions

## Configuration to UPDATE

### Environment Variables
- **`DAILY_EXECUTION_TIME`** - Consider deprecating this in favor of market hours settings
- **Railway Configuration** - Update to use unified scheduler entry point

### Agent Configuration
- **`/config/agents.json`** - Ensure agent configurations are compatible with market hours execution

### Database Schema
- Review if any database fields or queries reference evening execution timing that should be updated

## Recommendations for Code Cleanup

### Immediate Actions (High Priority)
1. **Update Railway Deployment**: Change Railway to use `python3 main.py start` instead of legacy scheduler scripts
2. **Consolidate Systemd Services**: Create single unified service or update existing services for market hours
3. **Remove Debug Scripts**: Delete temporary Railway debugging scripts that are no longer needed

### Secondary Actions (Medium Priority)  
1. **Update Documentation**: Comprehensive update of all timing references from evening to market hours
2. **Configuration Cleanup**: Remove or deprecate unused 21:30 execution settings
3. **Command Deprecation**: Consider deprecating separate `scheduler` and `intraday` commands in favor of unified `start`

### Low Priority (Nice to Have)
1. **Test Suite Update**: Ensure tests reflect unified market hours approach
2. **Logging Cleanup**: Update log messages that reference evening execution
3. **Monitoring Updates**: Update any monitoring or alerting based on old execution times

### Conservative Approach
- **Keep** `daily_runner.py` as it may still be used by the `main.py scheduler` command
- **Keep** one Railway script (probably `railway_scheduler.py`) until confirmed that unified approach works in Railway
- **Keep** separate systemd services initially and consolidate after confirming unified approach works in production
- **Archive** rather than delete debug scripts in case Railway issues resurface

### Risk Mitigation
- Test unified scheduler thoroughly in Railway environment before removing legacy scripts
- Ensure all production deployments are updated before removing systemd services
- Maintain git history of deleted files for easy recovery if needed
- Update deployment documentation before making infrastructure changes