# Triage Report: Andy Grok Agent TechnicalTradeDecision 'amount' Parameter Error

## Summary
- **Symptom**: `__init__() got an unexpected keyword argument 'amount'` when creating TechnicalTradeDecision
- **Scope/Blast Radius**: Andy Grok Agent only - affects RSI-based SPY trading functionality
- **First Seen**: Current session when agent tries to create trade decisions
- **Environments Affected**: All environments running Andy Grok Agent
- **Related Components**: Technical agent framework, CongressionalTrade dataclass

## Likely Components & Paths
- **Primary Subsystem**: Technical Agent Framework → Andy Grok Agent implementation
- **Secondary Subsystem**: Data Layer → CongressionalTrade dataclass definition
- **Candidate paths**:
  - `/Users/admin/github/trading-automation/src/agents/technical_agent.py` (lines 117-127)
  - `/Users/admin/github/trading-automation/src/data/quiver_client.py` (lines 21-32)
  - `/Users/admin/github/trading-automation/src/agents/andy_grok_agent.py` (indirect usage)

## Ranked Hypotheses

1) **CongressionalTrade dataclass schema mismatch** — Confidence: 95
   - **Mechanism**: The `_create_dummy_source_trade` method in TechnicalAgent is trying to create a CongressionalTrade with an `amount` parameter, but the CongressionalTrade dataclass was refactored to use `amount_range`, `amount_min`, and `amount_max` instead
   - **Evidence for**: 
     - CongressionalTrade dataclass (lines 21-32) shows fields: `amount_range`, `amount_min`, `amount_max` but NO `amount` field
     - `_create_dummy_source_trade` method (lines 117-127) still uses old `amount=0` parameter
     - Error message matches exactly: "unexpected keyword argument 'amount'"
   - **Evidence against**: None - error location and dataclass structure confirm this
   - **Quick validation**: Check `_create_dummy_source_trade` method parameters vs CongressionalTrade dataclass fields
   - **Expected observation if true**: Changing the dummy trade creation to use the new field structure will fix the error

2) **Import/module loading issue with CongressionalTrade** — Confidence: 5
   - **Mechanism**: Wrong version of CongressionalTrade class being imported due to module caching or path issues
   - **Evidence for**: Complex inheritance structure with multiple dataclasses
   - **Evidence against**: Direct inspection shows correct CongressionalTrade import and structure
   - **Quick validation**: Import test confirmed correct CongressionalTrade class is loaded
   - **Expected observation if true**: Module reload or import path change would resolve issue

## High-Signal Checks (Do First)
- [x] **Verify CongressionalTrade dataclass structure**: CONFIRMED - uses `amount_range`, `amount_min`, `amount_max`
- [x] **Check TechnicalAgent._create_dummy_source_trade method**: CONFIRMED - uses deprecated `amount=0` parameter
- [ ] **Test fix by updating dummy trade creation to use new schema**
- [ ] **Verify TechnicalTradeDecision inheritance chain is intact**

## Recent Changes (last 20 commits touching suspects)
Based on git status, recent changes include:
- Modified `src/agents/technical_agent.py` 
- Modified `src/utils/exceptions.py`
- Previous dataclass conversions likely changed CongressionalTrade schema

## Data Gaps & Requests
- Need: Confirm when CongressionalTrade schema was changed from `amount` to `amount_range/min/max`
- Need: Verify if other agents are also affected by this schema change
- Need: Check if there are any other references to old `amount` field in codebase

## Handoff to Debugger subagent
- **Start with**: `/Users/admin/github/trading-automation/src/agents/technical_agent.py` lines 117-127 (`_create_dummy_source_trade` method)
- **Try to falsify Hypothesis #1** via updating the CongressionalTrade creation parameters:
  - Change `amount=0` to `amount_range="$0"`, `amount_min=0`, `amount_max=0`
- **If successful**: Run Andy Grok Agent to verify trade decision creation works
- **Also check**: Search codebase for any other references to `CongressionalTrade(.*amount=` pattern
- **Expected result**: Andy Grok Agent should successfully create TechnicalTradeDecision objects and proceed with RSI analysis

## Root Cause Analysis
The misleading error message "TechnicalTradeDecision got unexpected keyword argument 'amount'" occurs because the error originates from within the TechnicalTradeDecision constructor when it tries to create its `source_trade` parameter via `_create_dummy_source_trade()`. The actual error is that CongressionalTrade no longer accepts an `amount` parameter - it was refactored to use `amount_range`, `amount_min`, and `amount_max` fields instead.

## Resolution Path
1. Update `TechnicalAgent._create_dummy_source_trade()` method to use new CongressionalTrade schema
2. Verify fix by running Andy Grok Agent RSI analysis
3. Search for and update any other obsolete CongressionalTrade instantiations
4. Add regression test to prevent future schema mismatch issues