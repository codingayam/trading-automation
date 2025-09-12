# Triage Report: Docker Configuration Cleanup Analysis

## Summary
- **Symptom:** Multiple Docker configuration files exist with unclear usage status
- **Scope/Blast Radius:** Repository maintenance and deployment clarity
- **First Seen / Last Known Good:** N/A - ongoing maintenance issue
- **Environments Affected:** Development, Production, Railway deployment
- **Related Tickets/Deploys/Flags:** Railway deployment is primary production target

## Likely Components & Paths
- **Container Configuration** → Multiple Dockerfile variants causing confusion
- **Deployment Orchestration** → Docker Compose files for different environments
- **Candidate paths:**
  - `/Users/admin/github/trading-automation/Dockerfile` (development/local)
  - `/Users/admin/github/trading-automation/Dockerfile.railway` (Railway production - ACTIVE)
  - `/Users/admin/github/trading-automation/Dockerfile.production` (legacy production - OBSOLETE)
  - `/Users/admin/github/trading-automation/docker-compose.yml` (development - ACTIVE)
  - `/Users/admin/github/trading-automation/docker-compose.production.yml` (legacy production - OBSOLETE)
  - `/Users/admin/github/trading-automation/deployment/deploy.sh` (legacy systemd deployment - OBSOLETE)

## Ranked Hypotheses

### 1) Railway-specific configuration is actively used, other production configs are obsolete — Confidence: 95
   - **Mechanism:** Railway deployment explicitly references `Dockerfile.railway` in `railway.json`, making it the sole production container
   - **Evidence for:** 
     - `railway.json` line 5: `"dockerfilePath": "Dockerfile.railway"`
     - Documentation mentions Railway as primary deployment platform
     - `Dockerfile.railway` includes Railway-specific configurations (supervisord, all-in-one setup)
   - **Evidence against:** None - Railway configuration is clearly referenced and documented
   - **Quick validation:** Check Railway dashboard deployment logs for Dockerfile usage
   - **Expected observation if true:** Railway successfully builds using `Dockerfile.railway`

### 2) Legacy production configurations are no longer needed — Confidence: 90
   - **Mechanism:** System evolved from complex multi-service production setup to Railway single-container deployment
   - **Evidence for:** 
     - `docker-compose.production.yml` references missing `Dockerfile.dashboard` (line 80)
     - `Dockerfile.production` uses old Python 3.9, while Railway uses newer versions
     - `deployment/deploy.sh` is systemd-based, conflicts with Railway container approach
     - Documentation explicitly states Railway as "recommended" deployment
   - **Evidence against:** Files might be used for alternative deployment scenarios
   - **Quick validation:** Check git logs for recent usage of these files
   - **Expected observation if true:** No recent commits or references to production files

### 3) Development docker-compose is still valid for local testing — Confidence: 85
   - **Mechanism:** Local development needs container orchestration separate from Railway
   - **Evidence for:** 
     - `docker-compose.yml` references standard `Dockerfile` for development
     - Documentation includes docker-compose commands
     - Mounts local directories for development workflow
   - **Evidence against:** May be outdated compared to Railway setup
   - **Quick validation:** Test `docker-compose up` functionality
   - **Expected observation if true:** Successful local container startup

### 4) Base Dockerfile serves development/testing purposes — Confidence: 75
   - **Mechanism:** Standard Dockerfile used for local development and referenced by docker-compose
   - **Evidence for:** 
     - Multi-stage build optimized for development
     - Referenced by `docker-compose.yml`
     - Uses newer Python 3.11
   - **Evidence against:** May duplicate functionality of Railway Dockerfile
   - **Quick validation:** Check if docker-compose build succeeds
   - **Expected observation if true:** Successful image build for local development

## High-Signal Checks (Do First)
- [ ] Test Railway deployment to confirm `Dockerfile.railway` is actively used
- [ ] Check git log for recent commits touching `Dockerfile.production` and `docker-compose.production.yml`
- [ ] Test local development: `docker-compose build && docker-compose up`
- [ ] Verify `Dockerfile.dashboard` does not exist (referenced in production compose but missing)
- [ ] Check deployment/nginx configs referenced in production compose for existence

## Recent Changes (last 20 commits touching suspects)
- No specific commit analysis available in current context
- Railway deployment has been primary focus based on documentation

## Data Gaps & Requests
- **Need:** Git log analysis of Docker file usage over last 6 months
- **Need:** Railway deployment logs showing which Dockerfile is actually built
- **Need:** Test results of `docker-compose up` for development workflow
- **Need:** Verification that referenced nginx/grafana configs exist for production setup

## File Inventory & Usage Analysis

### ACTIVELY USED FILES
1. **`Dockerfile.railway`** - ✅ **KEEP**
   - **Purpose:** Railway production deployment
   - **Evidence:** Explicitly referenced in `railway.json`
   - **Features:** All-in-one container with supervisord, SQLite setup
   - **Risk of removal:** HIGH - would break Railway deployment

2. **`docker-compose.yml`** - ✅ **KEEP**
   - **Purpose:** Local development orchestration
   - **Evidence:** Referenced in development documentation
   - **Features:** Volume mounts, development environment setup
   - **Risk of removal:** MEDIUM - would break local development workflow

3. **`Dockerfile`** - ✅ **KEEP**
   - **Purpose:** Development/local container build
   - **Evidence:** Referenced by docker-compose.yml
   - **Features:** Multi-stage build, development optimizations
   - **Risk of removal:** MEDIUM - needed for docker-compose functionality

### OBSOLETE FILES
4. **`Dockerfile.production`** - ❌ **REMOVE**
   - **Purpose:** Legacy production deployment (pre-Railway)
   - **Evidence:** No active references, uses outdated Python 3.9
   - **Issues:** Outdated dependencies, replaced by Railway
   - **Risk of removal:** LOW - no active usage detected

5. **`docker-compose.production.yml`** - ❌ **REMOVE**
   - **Purpose:** Complex multi-service production setup
   - **Evidence:** References missing `Dockerfile.dashboard`, complex PostgreSQL/Redis/Nginx setup
   - **Issues:** References non-existent files, conflicts with Railway approach
   - **Risk of removal:** LOW - replaced by Railway single-container approach

## Cleanup Recommendations

### Priority 1 - Safe Removals (Low Risk)
```bash
# Remove obsolete production configurations
rm Dockerfile.production
rm docker-compose.production.yml
```
**Justification:** These files are legacy pre-Railway configurations with no active references and missing dependencies.

### Priority 2 - Verify Development Setup (Medium Risk)
```bash
# Test development workflow before making changes
docker-compose build
docker-compose up -d
docker-compose down
```
**Justification:** Ensure development workflow remains functional after cleanup.

### Priority 3 - Documentation Updates (Low Risk)
- Update documentation to remove references to removed files
- Clarify which Docker configurations are for which environments
- Document the Railway-first deployment strategy

## Handoff to Cleanup Process
- **Start with:** Remove `Dockerfile.production` and `docker-compose.production.yml`
- **Verify:** Railway deployment continues to function (uses `Dockerfile.railway`)
- **Test:** Local development workflow with remaining `Dockerfile` and `docker-compose.yml`
- **Monitor:** No broken references in documentation or scripts
- **Update:** Development documentation to reflect Railway-primary approach

## Cost-Benefit Analysis
**Benefits:**
- Reduced maintenance overhead (fewer Docker configs to maintain)
- Clearer deployment strategy (Railway-first approach)
- Eliminated confusion about which files are active
- Removed broken references (missing Dockerfile.dashboard)

**Risks:**
- Potential loss of alternative deployment options
- Need to recreate configs if Railway deployment becomes unsuitable
- Temporary disruption if development workflow breaks

**Recommendation:** Proceed with cleanup - benefits significantly outweigh risks given Railway's established role as primary deployment platform.