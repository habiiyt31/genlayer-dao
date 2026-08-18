# Testing DaoProposal

Step-by-step testing guide for the DaoProposal contract — AI-triaged governance proposal and voting.

---

## 📋 About This Contract

**Use case:** DAO members submit governance proposals. GenLayer LLM validators triage each proposal for quality and relevance before it enters token-weighted voting. Final tally determines PASSED or REJECTED.

**Key features tested:**
- DAO mission-based AI triage (prompt_comparative)
- Token-weighted voting with quorum enforcement
- State machine: PENDING → ACTIVE / REJECTED → PASSED / REJECTED → EXECUTED
- Member registration and voting power management

**Total methods:** 13 (7 view + 6 write)

> ⚠️ **You need 3 accounts:** Owner, Member A, Member B. Set up 3 accounts in Studio before starting.

---

**[Switch to Owner account]**

Load `contracts/dao_proposal.py`, deploy with:

| Field | Min | Example Value |
|---|---|---|
| `dao_name` | 3 chars | `GenLayerDAO` |
| `dao_mission` | 50 chars | `Fund and govern open-source AI tooling for the GenLayer ecosystem and its developer community.` |
| `voting_period_blocks` | 1 | `100` |
| `quorum_percent` | 1-100 | `51` |

Click **Deploy** → copy contract address.

---

## 🧪 Test Sequence

### Part 1: Verify Initial State (7 view methods)

**[Any account]**

| # | Method | Input | Expected |
|---|---|---|---|
| 1 | `get_dao_info()` | — | JSON with name, mission, 0 proposals, 0 members |
| 2 | `get_proposal_count()` | — | `"0"` |
| 3 | `get_member_count()` | — | `"0"` |
| 4 | `get_total_voting_power()` | — | `"0"` |

---

### Part 2: Register Members

**[Switch to Owner account]**

#### Step 5: `register_member(member_address, power)`

Register Member A with voting power 60:

- **Method:** `register_member`
- **Input:**
  - `member_address`: Member A's address
  - `power`: `60`
- **Expected:** ✅ Transaction success

#### Step 6: Register Member B with power 40

- **Method:** `register_member`
- **Input:**
  - `member_address`: Member B's address
  - `power`: `40`
- **Expected:** ✅ Transaction success

#### Step 7-8: Verify membership

| # | Method | Input | Expected |
|---|---|---|---|
| 7 | `get_member_count()` | — | `"2"` |
| 8 | `get_total_voting_power()` | — | `"100"` |
| 9 | `get_voting_power(memberA)` | Member A address | `"60"` |

---

### Part 3: Submit a Proposal (AI Triage)

**[Switch to Member A account]** (or any account — anyone can propose)

#### Step 10: `submit_proposal(title, description, action_url)`

- **Method:** `submit_proposal`
- **Input:**
  - `title`: `Increase validator node incentives by 15%`
  - `description`: `This proposal requests increasing the validator node reward pool by 15% to attract more node operators to the GenLayer network, improving decentralization and resilience against validator dropout.`
  - `action_url`: `https://gist.github.com/example/validator-incentives`
- **Expected:**
  - Wait **60-120 seconds** (web fetch + LLM evaluate + consensus)
  - Returns: `"ACTIVE <reason>"` or `"REJECTED <reason>"`

#### Step 11-12: Check triage result

| # | Method | Input | Expected |
|---|---|---|---|
| 11 | `get_proposal_state(0)` | `0` | `"ACTIVE"` or `"REJECTED"` |
| 12 | `get_proposal(0)` | `0` | Full JSON with all fields |

---

### Part 4: Triage Rejection Test

Submit a clearly off-topic or spammy proposal:

- **title:** `Buy my NFT collection it's great`
- **description:** `We should use DAO treasury to buy my personal NFT collection because it will definitely go up in value and make the DAO rich beyond all imagination please vote yes.`
- **action_url:** `https://example.com`
- **Expected:** ✅ `"REJECTED"` — AI filters out spam

---

### Part 5: Vote on ACTIVE Proposal

If proposal #0 reached ACTIVE state:

**[Switch to Member A account]**

#### Step 13: `vote(proposal_id, support)`

- **Method:** `vote`
- **Input:**
  - `proposal_id`: `0`
  - `support`: `true` (YES)
- **Expected:** ✅ Vote recorded with 60 power

**[Switch to Member B account]**

#### Step 14: Member B votes NO

- **Method:** `vote`
- **Input:**
  - `proposal_id`: `0`
  - `support`: `false`
- **Expected:** ✅ Vote recorded with 40 power

#### Step 15: Verify vote counts

| # | Method | Input | Expected |
|---|---|---|---|
| 15a | `get_proposal(0)` | `0` | `yes_votes: 60, no_votes: 40` |
| 15b | `has_voted(0, memberA)` | `0`, Member A addr | `"true"` |

---

### Part 6: Finalize Proposal

**[Any account]**

#### Step 16: `finalize_proposal(proposal_id)`

- **Method:** `finalize_proposal`
- **Input:** `0`
- **Expected:** `"PASSED"` (60 YES > 40 NO, quorum met: 100 ≥ 51)

#### Step 17: Verify

| # | Method | Expected |
|---|---|---|
| 17 | `get_proposal_state(0)` | `"PASSED"` |

---

### Part 7: Execute Proposal

**[Switch to Owner account]**

#### Step 18: `execute_proposal(proposal_id)`

- **Method:** `execute_proposal`
- **Input:** `0`
- **Expected:** ✅ State → `"EXECUTED"`

---

### Part 8: Quorum Failure Test

Deploy fresh contract with `quorum_percent: 80`.
Register 2 members with power 50 each (total = 100).
Submit a valid proposal → wait for ACTIVE.
Only Member A votes YES (50 power).

- **Method:** `finalize_proposal(0)`
- **Expected:** `"REJECTED: quorum not reached"` (50 < 80)

✅ Quorum enforcement working.

---

### Part 9: Error Handling

#### Cannot vote twice

**[Member A, on an ACTIVE proposal]**

- **Method:** `vote`, **Input:** `0, true`
- **Expected:** ❌ ERROR: `"dao: Already voted on this proposal"`

#### Non-member cannot vote

**[Any non-member account]**

- **Method:** `vote`, **Input:** `0, true`
- **Expected:** ❌ ERROR: `"dao: Not a registered member with voting power"`

#### Cannot finalize a PENDING proposal

- **Method:** `finalize_proposal(0)` (when still PENDING)
- **Expected:** ❌ ERROR: `"dao: Proposal is not ACTIVE"`

#### Non-owner cannot execute

**[Member A account]**

- **Method:** `execute_proposal(0)`
- **Expected:** ❌ ERROR: `"dao: Only owner can execute"`

#### Mission too short on deploy

Deploy with `dao_mission: "Short"` (< 50 chars):
- **Expected:** ❌ ERROR: `"dao: DAO mission must be at least 50 characters"`

---

## 🎯 Quick Demo (12 Minutes)

Happy path — full governance flow:

```
[Owner]
1. Deploy with mission >= 50 chars

2. register_member(memberA, 60) ✅
3. register_member(memberB, 40) ✅

[Member A]
4. submit_proposal(title, desc, url) → wait 90s → AI triages

[If ACTIVE]
[Member A]
5. vote(0, true)  → 60 power YES ✅

[Member B]
6. vote(0, false) → 40 power NO ✅

[Any]
7. finalize_proposal(0) → "PASSED" ✅

[Owner]
8. execute_proposal(0) → "EXECUTED" ✅
```

**Key talking points:**
- Step 4: "AI triage prevents spam from ever reaching voting — no gas wasted on junk proposals"
- Step 5-6: "Token-weighted voting — bigger stake = more say"
- Step 7: "Deterministic tally — no LLM needed, just arithmetic"
- Step 8: "On-chain record of execution — fully auditable"

---

## 📊 State Machine

```
submit_proposal()
       │
       ▼
   PENDING
  (AI triage)
  ┌────┴────┐
ACTIVE    REJECTED
  │
vote() × N
  │
finalize_proposal()
  ┌────┴────┐
PASSED   REJECTED
  │
execute_proposal()
  │
EXECUTED
```

---

## 📊 Full Test Summary

| Test | Status |
|---|---|
| Deploy with valid config | ✅ |
| Deploy rejected with short mission | ✅ |
| Initial state — 0 members, 0 proposals | ✅ |
| Register members with voting power | ✅ |
| Submit valid proposal → AI triages ACTIVE | ✅ |
| Submit spam proposal → AI triages REJECTED | ✅ |
| Member A votes YES → 60 power recorded | ✅ |
| Member B votes NO → 40 power recorded | ✅ |
| Cannot vote twice | ✅ |
| Non-member cannot vote | ✅ |
| Finalize → PASSED (YES majority, quorum met) | ✅ |
| Finalize → REJECTED (quorum not met) | ✅ |
| Owner executes PASSED proposal | ✅ |
| Non-owner blocked from executing | ✅ |

---

## 🔗 Back

← [Main README](../README.md)
