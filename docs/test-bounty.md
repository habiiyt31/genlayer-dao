# Testing DaoBounty

Step-by-step testing guide for the DaoBounty contract — multi-milestone bounty with per-milestone AI verification.

---

## 📋 About This Contract

**Use case:** DAO funds a bounty for a task split into milestones. Hunter claims it, submits deliverables per milestone. GenLayer LLM validators evaluate each milestone against its acceptance criteria. Payout is released progressively per approved milestone.

**Key features tested:**
- Multi-milestone structure with weights (must sum to 100)
- Per-milestone AI verification via strict_eq consensus
- Dispute → retry → arbiter → force-release safety valve
- Progressive payout on each approved milestone

**Total methods:** 14 (5 view + 9 write)

> ⚠️ **You need 3 accounts:** Owner, Hunter, Arbiter. Set up 3 accounts in Studio before starting.

---

**[Switch to Owner account]**

Load `contracts/dao_bounty.py`, deploy with:

| Field | Min | Example Value |
|---|---|---|
| `bounty_title` | 10 chars | `GenLayer Analytics Dashboard` |
| `bounty_description` | 60 chars | `Build a public dashboard showing GenLayer network stats: validator count, transaction volume, and contract call frequency.` |
| `milestone_titles_csv` | — | `Design mockups\|Frontend build\|Deploy and docs` |
| `milestone_criteria_csv` | — | `Figma file with 5+ screens shared publicly\|Functional React app with 3 live charts from real data\|Live URL accessible and README with setup instructions` |
| `milestone_weights_csv` | sum=100 | `20\|60\|20` |
| `arbiter_addr` | — | `0xARBITER_ADDRESS` |
| `max_dispute_attempts` | ≥ 2 | `2` |

> Pipe `|` separates each milestone field. The 3 CSV fields must have equal length arrays.

Click **Deploy** → copy contract address.

---

## 🧪 Test Sequence

### Part 1: Verify Initial State (5 view methods)

**[Any account]**

| # | Method | Input | Expected |
|---|---|---|---|
| 1 | `get_bounty_info()` | — | state: "OPEN", total_amount: 0 |
| 2 | `get_state()` | — | `"OPEN"` |
| 3 | `get_milestone_count()` | — | `"3"` |
| 4 | `get_current_milestone()` | — | `"0"` |
| 5 | `get_milestone(0)` | `0` | title: "Design mockups", state: "PENDING" |

---

### Part 2: Fund the Bounty

**[Switch to Owner account]**

#### Step 6: `fund_bounty()` — payable

- **Method:** `fund_bounty`
- **Value (GEN):** `5` (5 GEN bounty)
- **Expected:** ✅ Transaction success

#### Step 7: Verify funding

| # | Method | Expected |
|---|---|---|
| 7a | `get_contract_balance()` | `"5000000000000000000"` |
| 7b | `get_bounty_info()` | `total_amount_wei: 5000000000000000000` |

---

### Part 3: Claim the Bounty

**[Switch to Hunter account]**

#### Step 8: `claim_bounty()`

- **Method:** `claim_bounty`
- **Expected:** ✅ State → `"CLAIMED"`, hunter set to caller

#### Step 9: Verify claim

| # | Method | Expected |
|---|---|---|
| 9a | `get_state()` | `"CLAIMED"` |
| 9b | `get_bounty_info()` | `hunter: Hunter's address` |

---

### Part 4: Owner Cannot Claim Own Bounty

**[Switch to Owner account]**

Deploy fresh contract, fund it, then:

- **Method:** `claim_bounty`
- **Expected:** ❌ ERROR: `"dao: Owner cannot claim own bounty"`

✅ Self-claim protection working.

---

### Part 5: Submit Milestone 0 (AI Verification)

**[Switch to Hunter account]**

#### Step 10: `submit_milestone(deliverable_url, notes)`

- **Method:** `submit_milestone`
- **Input:**
  - `deliverable_url`: `https://github.com/cosmos/cosmos/blob/master/VALIDATORS_FAQ.md`
  - `notes`: `Completed 6 screens: overview, validators, transactions, contracts, block detail, and settings. All screens are interactive and linked.`
- **Expected:**
  - Wait **60-120 seconds** (web fetch + LLM strict_eq consensus)
  - Returns: `"APPROVED <reason>"` or `"REJECTED <reason>"`

#### Step 11: If APPROVED — check milestone 0

| # | Method | Input | Expected |
|---|---|---|---|
| 11a | `get_milestone(0)` | `0` | state: "APPROVED" |
| 11b | `get_current_milestone()` | — | `"1"` (advanced) |
| 11c | `get_bounty_info()` | — | milestones_approved: 1 |

> If APPROVED: Hunter receives 20% of 5 GEN = **1 GEN** instantly.

---

### Part 6: Submit Milestone 1 (Larger Payout)

**[Hunter account]**

#### Step 12: `submit_milestone(deliverable_url, notes)`

- **Method:** `submit_milestone`
- **Input:**
  - `deliverable_url`: `https://github.com/genlayerlabs/genlayer-studio`
  - `notes`: `React app deployed to Vercel. 3 live charts pulling from GenLayer testnet RPC: validator count over time, daily tx volume, and contract call heatmap.`
- **Expected:** ✅ `"APPROVED"` → Hunter receives 60% = **3 GEN**

---

### Part 7: Submit Milestone 2 (Final)

**[Hunter account]**

#### Step 13: `submit_milestone(deliverable_url, notes)`

- **Method:** `submit_milestone`
- **Input:**
  - `deliverable_url`: `https://github.com/genlayerlabs/genlayer-docs`
  - `notes`: `Live at the URL above. README covers local setup, environment variables, and how to point at mainnet when available.`
- **Expected:** ✅ `"APPROVED"` → Hunter receives 20% = **1 GEN**, state → `"COMPLETED"`

---

### Part 8: Dispute Flow

Redeploy. Fund. Claim (as Hunter). Submit a bad URL:

#### Step 14: `submit_milestone(url, notes)` — bad deliverable

- **URL:** `https://github.com/torvalds/linux/blob/master/README` (isi tidak relevan sama sekali dengan kriteria milestone)
- **Expected:** `"REJECTED"` — state → `"DISPUTED"`

#### Step 15: Check dispute state

| # | Method | Expected |
|---|---|---|
| 15a | `get_state()` | `"DISPUTED"` |
| 15b | `get_milestone(0)` | state: "DISPUTED" |
| 15c | `get_dispute_attempts()` | `"0"` |

---

### Part 8A: Hunter Retries (retry_milestone)

**[Hunter account]**

- **Method:** `retry_milestone`
- **Input:**
  - `new_url`: `https://github.com/cosmos/cosmos/blob/master/VALIDATORS_FAQ.md`
  - `notes`: `Fixed — now pointing to actual Figma file with all 6 screens.`
- **Expected:** ✅ Re-triggers AI verification, state → `"APPROVED"` (or DISPUTED again)

---

### Part 8B: Owner Override (owner_approve_milestone)

If still DISPUTED after retry:

**[Switch to Owner account]**

- **Method:** `owner_approve_milestone`
- **Expected:** ✅ Milestone APPROVED, payout released, advances to next milestone

---

### Part 8C: Arbiter Rules

**[Switch to Arbiter account]**

- **Method:** `arbiter_rule`
- **Input:** `approve`: `true`
- **Expected:** ✅ Milestone APPROVED, payout released

Or:

- **Input:** `approve`: `false`
- **Expected:** ✅ Milestone reset to PENDING for hunter to re-try

---

### Part 8D: Force Claim Payout (Safety Valve)

Get dispute_attempts to max (submit bad work twice):

1. Submit bad URL → DISPUTED (attempt 0)
2. `retry_milestone(bad_url)` → DISPUTED (attempt 1)
3. `retry_milestone(bad_url)` → DISPUTED (attempt 2 = max_dispute_attempts)

**[Hunter account]**

- **Method:** `force_claim_payout`
- **Expected:** ✅ Remaining balance → Hunter, state → `"COMPLETED"`

#### Force claim too early (should fail)

- **Method:** `force_claim_payout` (when dispute_attempts < max)
- **Expected:** ❌ ERROR: `"dao: Not enough dispute attempts. Current: 0, required: 2"`

---

### Part 9: Cancel Unclaimed Bounty

**[Owner account]**

Deploy fresh, fund it, do NOT claim:

- **Method:** `cancel_bounty`
- **Expected:** ✅ Balance → Owner, state → `"COMPLETED"`

#### Cannot cancel if already claimed

- **Method:** `cancel_bounty` (when CLAIMED)
- **Expected:** ❌ ERROR: `"dao: Can only cancel in OPEN state"`

---

### Part 10: Deployment Validation Tests

#### Weights not summing to 100

Deploy with `milestone_weights_csv: "30|30|30"` (sums to 90):
- **Expected:** ❌ ERROR: `"Milestone weights must sum to 100"`

#### Fewer than 2 milestones

Deploy with `milestone_titles_csv: "Only one"`:
- **Expected:** ❌ ERROR: `"Must have at least 2 milestones"`

---

## 🎯 Quick Demo (15 Minutes)

Full bounty flow — happy path:

```
[Owner]
1. Deploy: 3 milestones, weights 20|60|20

2. fund_bounty()  Value: 5 GEN ✅

[Hunter]
3. claim_bounty() → state: CLAIMED ✅

4. submit_milestone(cosmos_validators_url, notes)
   → wait 90s → AI strict_eq evaluates
   → APPROVED → 1 GEN to Hunter ✅ (20%)

5. submit_milestone(github_url, notes)
   → wait 90s → APPROVED → 3 GEN to Hunter ✅ (60%)

6. submit_milestone(live_url, notes)
   → wait 90s → APPROVED → 1 GEN to Hunter ✅ (20%)
   → state: COMPLETED ✅

[Show dispute safety valve]
7. (Redeploy) submit bad URL → DISPUTED
8. retry_milestone(bad) × 2 → dispute_attempts = 2
9. force_claim_payout() → remaining GEN to Hunter ✅
```

**Key talking points:**
- Step 4-6: "Each milestone is verified independently — Hunter gets paid progressively, not all at once"
- "strict_eq consensus means ALL validators must agree exactly — no ambiguity on payment gates"
- Step 9: "Force-release prevents funds being locked forever if owner goes offline"

---

## 📊 State Machine

```
OPEN
 │
 ├── fund_bounty() (repeatable)
 │
 └── claim_bounty()
          │
       CLAIMED
          │
       submit_milestone()
          │
        AI evaluates (strict_eq)
       ┌──┴──┐
   APPROVED  DISPUTED
       │          │
  [payout %]  retry_milestone() ──→ re-evaluate
       │          │
  next milestone  owner_approve / arbiter_rule / force_claim
       │
  (repeat per milestone)
       │
  COMPLETED
```

---

## 📊 Full Test Summary

| Test | Status |
|---|---|
| Deploy with valid milestones (sum=100) | ✅ |
| Deploy rejected if weights ≠ 100 | ✅ |
| Deploy rejected if < 2 milestones | ✅ |
| Initial state OPEN, zero balance | ✅ |
| Owner funds bounty | ✅ |
| Hunter claims → CLAIMED | ✅ |
| Owner cannot claim own bounty | ✅ |
| Submit M0 good URL → APPROVED + payout 20% | ✅ |
| Submit M1 good URL → APPROVED + payout 60% | ✅ |
| Submit M2 good URL → APPROVED + payout 20%, COMPLETED | ✅ |
| Submit bad URL → DISPUTED | ✅ |
| retry_milestone with better URL → re-evaluates | ✅ |
| owner_approve_milestone overrides AI | ✅ |
| arbiter_rule approve/reject | ✅ |
| force_claim_payout after max attempts | ✅ |
| force_claim_payout blocked before threshold | ✅ |
| cancel_bounty refunds owner | ✅ |
| Cannot cancel after claim | ✅ |

---

## 🔗 Back

← [Main README](../README.md)
