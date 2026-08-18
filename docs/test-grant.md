# Testing DaoGrant

Step-by-step testing guide for the DaoGrant contract — AI-scored grant allocator with rubric-based evaluation.

---

## 📋 About This Contract

**Use case:** DAO treasury funds a grant round. Applicants submit projects. GenLayer LLM validators score each application against a 3-dimension rubric (impact, feasibility, originality). Top N projects auto-receive funds.

**Key features tested:**
- Rubric-based AI scoring: prompt_comparative for tier agreement
- Score tiers: HIGH (≥22 points), MEDIUM (14-21), LOW (≤13)
- Treasury funding and safe withdrawal
- State machine: OPEN → REVIEW → SCORED → DISTRIBUTED

**Total methods:** 12 (7 view + 5 write)

> ⚠️ **You need 3 accounts:** Owner, Applicant A, Applicant B. Set up in Studio first.

---

**[Switch to Owner account]**

Load `contracts/dao_grant.py`, deploy with:

| Field | Min | Example Value |
|---|---|---|
| `grant_name` | 3 chars | `Q3 GenLayer OSS Grant` |
| `grant_purpose` | 60 chars | `Fund open-source developer tools that improve the GenLayer developer experience and ecosystem growth.` |
| `rubric_impact` | 30 chars | `Does this project meaningfully unblock other builders or improve real user outcomes on GenLayer?` |
| `rubric_feasibility` | 30 chars | `Can this team realistically ship in 3 months given their track record and stated plan?` |
| `rubric_originality` | 30 chars | `Is this solving a problem that existing tools or projects do not already solve well?` |
| `max_winners` | 1 | `2` |

Click **Deploy** → copy contract address.

---

## 🧪 Test Sequence

### Part 1: Verify Initial State (7 view methods)

**[Any account]**

| # | Method | Input | Expected |
|---|---|---|---|
| 1 | `get_grant_info()` | — | JSON with state: "OPEN", pool: 0 |
| 2 | `get_state()` | — | `"OPEN"` |
| 3 | `get_application_count()` | — | `"0"` |
| 4 | `get_contract_balance()` | — | `"0"` |
| 5 | `get_rubric()` | — | JSON with all 3 rubric dimensions |

---

### Part 2: Fund the Treasury

**[Switch to Owner account]**

#### Step 6: `fund_treasury()` — payable

- **Method:** `fund_treasury`
- **Value (GEN):** `10` (10 GEN for the grant pool)
- **Expected:** ✅ Transaction success

#### Step 7: Verify funding

| # | Method | Expected |
|---|---|---|
| 7a | `get_contract_balance()` | `"10000000000000000000"` |
| 7b | `get_grant_info()` | `total_pool_wei: 10000000000000000000` |

---

### Part 3: Submit Applications (AI Scoring)

**[Switch to Applicant A account]**

#### Step 8: `submit_application(title, description, project_url)` — HIGH score expected

- **Method:** `submit_application`
- **Input:**
  - `title`: `GenLayer Contract Testing Framework`
  - `description`: `An automated testing framework for GenLayer Intelligent Contracts that enables local simulation of validator consensus, mock LLM responses, and CI/CD integration. Addresses the biggest pain point for GenLayer devs today.`
  - `project_url`: `https://github.com/genlayerlabs/genlayer-testing-suite`
- **Expected:**
  - Wait **60-120 seconds**
  - Returns verdict with `TIER:HIGH` and score ~25

**[Switch to Applicant B account]**

#### Step 9: Submit second application — MEDIUM score expected

- **Method:** `submit_application`
- **Input:**
  - `title`: `GenLayer Block Explorer`
  - `description`: `A simple block explorer for GenLayer testnet that shows transactions, contract calls, and validator votes. Uses the public GenLayer RPC. Will be maintained for 6 months after delivery.`
  - `project_url`: `https://github.com/genlayerlabs/genlayer-studio`
- **Expected:** Returns verdict, likely `TIER:MEDIUM`

#### Step 10: Verify scores

| # | Method | Input | Expected |
|---|---|---|---|
| 10a | `get_application_count()` | — | `"2"` |
| 10b | `get_application_score(0)` | `0` | `"25"` (HIGH) |
| 10c | `get_application_score(1)` | `1` | `"15"` (MEDIUM) |
| 10d | `get_application(0)` | `0` | Full JSON with verdict |

---

### Part 4: Submit Low-Quality Application

**[Any account]**

- **title:** `My Awesome Idea`
- **description:** `I have this idea to make GenLayer better. I will build something cool that will definitely help the ecosystem grow. Trust me it will be great and everyone will use it.`
- **project_url:** `https://github.com/torvalds/linux/blob/master/README`
- **Expected:** Returns verdict with `TIER:LOW`, score ~8 — Linux kernel README tidak nyambung sama sekali dengan grant purpose

✅ AI filters low-quality applications correctly.

---

### Part 5: Close Applications

**[Switch to Owner account]**

#### Step 11: `close_applications()`

- **Method:** `close_applications`
- **Expected:** ✅ State → `"REVIEW"`

#### Step 12: Verify state

| # | Method | Expected |
|---|---|---|
| 12 | `get_state()` | `"REVIEW"` |

#### Cannot submit after closing

**[Applicant A]**

- **Method:** `submit_application`
- **Expected:** ❌ ERROR: `"dao: Grant round is not accepting applications"`

---

### Part 6: Finalize Scoring

**[Switch to Owner account]**

#### Step 13: `finalize_scoring()`

- **Method:** `finalize_scoring`
- **Expected:** ✅ State → `"SCORED"`

---

### Part 7: Distribute Funds

**[Switch to Owner account]**

#### Step 14: `distribute()`

- **Method:** `distribute`
- **Expected:** ✅ Top 2 winners paid, state → `"DISTRIBUTED"`

With 10 GEN pool and 2 winners:
- Each winner receives **5 GEN** (10 ÷ 2)

> Note: Applicant C (LOW score) receives nothing.

#### Step 15: Verify distribution

| # | Method | Input | Expected |
|---|---|---|---|
| 15a | `get_state()` | — | `"DISTRIBUTED"` |
| 15b | `get_application(0)` | `0` | `funded_wei: 5000000000000000000` |
| 15c | `get_application(1)` | `1` | `funded_wei: 5000000000000000000` |

---

### Part 8: Withdraw Remainder

If total_pool was 10 GEN but only 9.99 GEN distributed (integer division dust):

**[Owner account]**

- **Method:** `withdraw_remainder`
- **Expected:** ✅ Remaining dust returned to owner

---

### Part 9: Error Handling

#### Non-owner cannot fund

**[Applicant A]**

- **Method:** `fund_treasury`, **Value:** `5`
- **Expected:** ❌ ERROR: `"dao: Only owner can fund treasury"`

#### Cannot distribute before scoring

**[Owner, in REVIEW state]**

- **Method:** `distribute`
- **Expected:** ❌ ERROR: `"dao: Not in SCORED state"`

#### Cannot close with zero applications

Deploy fresh contract, do NOT submit anything:

- **Method:** `close_applications`
- **Expected:** ❌ ERROR: `"dao: No applications submitted"`

#### Purpose too short on deploy

Deploy with `grant_purpose: "Too short"` (< 60 chars):
- **Expected:** ❌ ERROR: `"Grant purpose must be at least 60 characters"`

---

## 🎯 Quick Demo (15 Minutes)

Full grant round — happy path:

```
[Owner]
1. Deploy with rubric (all fields >= 30 chars)

2. fund_treasury()  Value: 10 GEN → balance: 10 GEN ✅

[Applicant A]
3. submit_application(title, desc, url) → wait 90s → TIER:HIGH ✅

[Applicant B]
4. submit_application(title, desc, url) → wait 90s → TIER:MEDIUM ✅

[Owner]
5. close_applications() → state: REVIEW ✅
6. finalize_scoring()   → state: SCORED ✅
7. distribute()         → top 2 paid, state: DISTRIBUTED ✅

[Optional cleanup]
8. withdraw_remainder() → dust returned to owner ✅
```

**Key talking points:**
- Step 3-4: "AI evaluates each application independently against the rubric — no human committee needed"
- Step 7: "Funds go directly to winners' wallets in one transaction — no manual disbursement"
- "The rubric is set at deploy time and cannot change mid-round — applicants know exactly how they're judged"

---

## 📊 State Machine

```
OPEN
 │
 ├── fund_treasury() (repeatable)
 │
 ├── submit_application() × N → AI scores each
 │
 └── close_applications()
          │
        REVIEW
          │
        finalize_scoring()
          │
        SCORED
          │
        distribute()
          │
      DISTRIBUTED
          │
        withdraw_remainder() (optional)
```

---

## 📊 Full Test Summary

| Test | Status |
|---|---|
| Deploy with valid rubric | ✅ |
| Deploy rejected with short purpose | ✅ |
| Initial state OPEN, zero balance | ✅ |
| Owner funds treasury | ✅ |
| Non-owner blocked from funding | ✅ |
| Submit strong application → TIER:HIGH | ✅ |
| Submit average application → TIER:MEDIUM | ✅ |
| Submit weak application → TIER:LOW | ✅ |
| Close applications → REVIEW | ✅ |
| Cannot submit after close | ✅ |
| Finalize scoring → SCORED | ✅ |
| Distribute → top N winners paid equally | ✅ |
| Cannot distribute before scoring | ✅ |
| Withdraw remainder after distribution | ✅ |

---

## 🔗 Back

← [Main README](../README.md)
