# Testing DaoVeto

Step-by-step testing guide for the DaoVeto contract — constitutional AI veto for on-chain governance actions.

---

## 📋 About This Contract

**Use case:** DAO stores its "constitution" on-chain. Before any governance action is executed, it passes through this contract. GenLayer validators check whether the action violates any rule. VETOED = blocked. ALLOWED = can proceed.

**Key features tested:**
- Constitution management: edit → seal (irreversible)
- AI veto check via prompt_comparative
- Checker registry (who can submit actions)
- Stats tracking: total allowed vs vetoed

**Total methods:** 14 (8 view + 6 write)

> ⚠️ **You need 2 accounts:** Owner, Checker. Set up in Studio first.

---

**[Switch to Owner account]**

Load `contracts/dao_veto.py`, deploy with:

| Field | Min | Example Value |
|---|---|---|
| `dao_name` | 3 chars | `GenLayerDAO` |
| `constitution` | 100 chars | See example below |

Constitution example (copy-paste):
```
1. The DAO may not allocate more than 20% of the treasury in a single vote.
2. No single member may hold more than 40% of total voting power.
3. Changes to this constitution require a 80% supermajority vote.
4. All funded projects must publish their code under an open-source license.
5. The DAO may not fund projects that have undisclosed conflicts of interest.
```

Click **Deploy** → copy contract address.

---

## 🧪 Test Sequence

### Part 1: Verify Initial State (8 view methods)

**[Any account]**

| # | Method | Input | Expected |
|---|---|---|---|
| 1 | `get_dao_info()` | — | sealed: false, 0 checks |
| 2 | `is_sealed()` | — | `"false"` |
| 3 | `get_constitution()` | — | Full constitution text |
| 4 | `get_check_count()` | — | `"0"` |
| 5 | `get_stats()` | — | `total_checks: 0, allowed: 0, vetoed: 0` |

---

### Part 2: Update Constitution (Before Sealing)

**[Owner account]**

#### Step 6: `update_constitution(new_constitution)`

- **Method:** `update_constitution`
- **Input:** Add a 6th rule:
```
1. The DAO may not allocate more than 20% of the treasury in a single vote.
2. No single member may hold more than 40% of total voting power.
3. Changes to this constitution require a 80% supermajority vote.
4. All funded projects must publish their code under an open-source license.
5. The DAO may not fund projects that have undisclosed conflicts of interest.
6. Emergency spending requires approval from at least 3 council members.
```
- **Expected:** ✅ Constitution updated

#### Step 7: Verify update

| # | Method | Expected |
|---|---|---|
| 7 | `get_constitution()` | Now shows 6 rules |

---

### Part 3: Seal the Constitution

**[Owner account]**

#### Step 8: `seal_constitution()`

- **Method:** `seal_constitution`
- **Expected:** ✅ Sealed forever

#### Step 9: Verify sealed

| # | Method | Expected |
|---|---|---|
| 9 | `is_sealed()` | `"true"` |

#### Cannot update after sealing

- **Method:** `update_constitution` (with any text)
- **Expected:** ❌ ERROR: `"dao: Constitution is sealed and cannot be modified"`

---

### Part 4: Register a Checker

**[Owner account]**

#### Step 10: `register_checker(checker_address)`

- **Method:** `register_checker`
- **Input:** Checker account address
- **Expected:** ✅ Checker registered

#### Step 11: Verify

| # | Method | Input | Expected |
|---|---|---|---|
| 11a | `is_checker(checker)` | Checker addr | `"true"` |
| 11b | `get_dao_info()` | — | `checker_count: 1` |

---

### Part 5: Submit ALLOWED Action

**[Switch to Checker account]**

#### Step 12: `submit_for_review(title, description, action_url)` — ALLOWED expected

- **Method:** `submit_for_review`
- **Input:**
  - `title`: `Allocate 5% treasury to dev grants`
  - `description`: `Proposal to allocate 5% of the current DAO treasury (well within the 20% cap) to fund 3 open-source developer tool projects for Q4.`
  - `action_url`: `https://gist.github.com/example/dao-proposal-5pct`
- **Expected:**
  - Wait **60-120 seconds**
  - Returns: `"ALLOWED no violations found"` (5% < 20% cap, open-source = rule 4 satisfied)

#### Step 13: Verify check #0

| # | Method | Input | Expected |
|---|---|---|---|
| 13a | `get_check_state(0)` | `0` | `"ALLOWED"` |
| 13b | `is_allowed(0)` | `0` | `"true"` |
| 13c | `get_check(0)` | `0` | Full JSON with verdict |
| 13d | `get_stats()` | — | `total_allowed: 1, total_vetoed: 0` |

---

### Part 6: Submit VETOED Action

**[Checker account]**

#### Step 14: `submit_for_review` — VETOED expected (violates Rule 1)

- **Method:** `submit_for_review`
- **Input:**
  - `title`: `Allocate 50% treasury to marketing`
  - `description`: `Emergency proposal to allocate 50% of the DAO treasury to a marketing campaign targeting enterprise customers. The team believes this will 10x the number of validators in 6 months.`
  - `action_url`: `https://gist.github.com/example/dao-proposal-50pct`
- **Expected:**
  - Wait **60-120 seconds**
  - Returns: `"VETOED Rule 1 violated: 50% exceeds the 20% single-vote allocation cap"` ✅

#### Step 15: Verify check #1

| # | Method | Input | Expected |
|---|---|---|---|
| 15a | `get_check_state(1)` | `1` | `"VETOED"` |
| 15b | `is_allowed(1)` | `1` | `"false"` |
| 15c | `get_stats()` | — | `total_allowed: 1, total_vetoed: 1` |

---

### Part 7: Submit Another VETOED Action (Different Rule)

**[Checker account]**

#### Step 16: Violate Rule 2 — voting power concentration

- **title:** `Give founding team 60% voting power`
- **description:** `Proposal to restructure the DAO token allocation so that the founding team holds 60% of voting power to enable faster decision making and reduce governance gridlock on critical protocol decisions.`
- **action_url:** `https://gist.github.com/example/dao-proposal-power`
- **Expected:** `"VETOED Rule 2 violated: 60% exceeds the 40% single-member voting power cap"` ✅

---

### Part 8: Owner Can Submit Without Being Registered

**[Owner account]**

- **Method:** `submit_for_review`
- **Input:**
  - `title`: `Owner direct review test`
  - `description`: `Testing that the owner can submit governance actions for constitutional review without needing to be in the checker registry.`
  - `action_url`: `https://example.com`
- **Expected:** ✅ No "Not a registered checker" error — owner always has access

---

### Part 9: Unregistered Account Blocked

**[Any non-checker, non-owner account]**

- **Method:** `submit_for_review`
- **Input:** Any valid values
- **Expected:** ❌ ERROR: `"dao: Not a registered checker"`

---

### Part 10: Remove Checker

**[Owner account]**

#### Step 17: `remove_checker(checker_address)`

- **Method:** `remove_checker`
- **Input:** Checker address
- **Expected:** ✅ Checker removed

#### Step 18: Verify removed

| # | Method | Input | Expected |
|---|---|---|---|
| 18a | `is_checker(checker)` | Checker addr | `"false"` |
| 18b | `get_dao_info()` | — | `checker_count: 0` |

**[Checker account — now removed]**

- **Method:** `submit_for_review`
- **Expected:** ❌ ERROR: `"dao: Not a registered checker"` ✅

---

### Part 11: Cannot Submit Before Sealing

Deploy fresh contract. Do NOT seal. Register a checker.

**[Checker account]**

- **Method:** `submit_for_review`
- **Expected:** ❌ ERROR: `"dao: Constitution must be sealed before submitting checks"`

✅ Prevents checks against an unstable constitution.

---

### Part 12: Deployment Validation Tests

#### Constitution too short

Deploy with `constitution: "Short"` (< 100 chars):
- **Expected:** ❌ ERROR: `"Constitution must be at least 100 characters"`

#### Seal already sealed

Call `seal_constitution()` a second time:
- **Expected:** ❌ ERROR: `"dao: Already sealed"`

---

## 🎯 Quick Demo (12 Minutes)

Full veto lifecycle — happy path:

```
[Owner]
1. Deploy with 5-rule constitution (>= 100 chars)

2. update_constitution(6 rules) ✅ (optional edit before seal)

3. seal_constitution() → is_sealed: true ✅

4. register_checker(checker_addr) ✅

[Checker]
5. submit_for_review("Allocate 5%...", desc, url)
   → wait 90s → AI evaluates vs constitution
   → "ALLOWED no violations found" ✅
   → is_allowed(0) = true ✅

6. submit_for_review("Allocate 50%...", desc, url)
   → wait 90s → AI evaluates
   → "VETOED Rule 1 violated: 50% > 20% cap" ✅
   → is_allowed(1) = false ✅

[Show stats]
7. get_stats() → allowed: 1, vetoed: 1 ✅
```

**Key talking points:**
- Step 3: "Once sealed, the constitution is immutable — even the owner cannot change it. This is the core trust guarantee."
- Step 5-6: "AI reads the same on-chain constitution as every other validator — no one gets a different ruleset"
- "Downstream contracts can call `is_allowed(check_id)` before executing — this becomes a trustless pre-execution layer"

---

## 📊 State Machine (Per Check)

```
submit_for_review()
        │
        ▼
    PENDING
        │
   AI evaluates constitution
   (prompt_comparative)
   ┌────┴────┐
ALLOWED   VETOED
```

---

## 🔗 Integration Pattern

`DaoVeto` is designed to be queried by other contracts before executing:

```python
# In dao_proposal.py execute_proposal():
# (pseudocode — not in this package, but shows the composability)

veto_contract = DaoVeto(veto_address)
check_id = veto_contract.submit_for_review(title, description, url)
assert veto_contract.is_allowed(check_id), "Blocked by constitutional veto"
# ... proceed with execution
```

This composability is what makes `dao_veto.py` a genuine **governance primitive** — not just a standalone contract.

---

## 📊 Full Test Summary

| Test | Status |
|---|---|
| Deploy with valid constitution | ✅ |
| Deploy rejected with short constitution | ✅ |
| Initial state: unsealed, 0 checks | ✅ |
| Update constitution before sealing | ✅ |
| Seal constitution → irreversible | ✅ |
| Cannot update after sealing | ✅ |
| Cannot seal twice | ✅ |
| Register checker | ✅ |
| Remove checker | ✅ |
| Removed checker blocked from submitting | ✅ |
| Non-checker blocked from submitting | ✅ |
| Cannot submit before sealing | ✅ |
| Submit compliant action → ALLOWED | ✅ |
| Submit 20%+ treasury action → VETOED (Rule 1) | ✅ |
| Submit 60% voting power action → VETOED (Rule 2) | ✅ |
| Owner can submit without being registered checker | ✅ |
| Stats tracking: allowed/vetoed counts | ✅ |
| is_allowed() returns correct bool | ✅ |

---

## 🔗 Back

← [Main README](../README.md)
