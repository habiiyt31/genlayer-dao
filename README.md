# genlayer-dao

> **DAO & Governance Intelligent Contracts for GenLayer**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GenLayer](https://img.shields.io/badge/Built%20on-GenLayer-orange)](https://docs.genlayer.com)
[![PyPI](https://img.shields.io/pypi/v/genlayer-dao)](https://pypi.org/project/genlayer-dao/)

A library of **4 production-ready Intelligent Contracts** that bring AI-powered DAO governance onto the GenLayer blockchain. Run proposals, grant rounds, bounties, and constitutional vetoes — all with trustless LLM consensus, no server, no admin key, no middleman.

---

## What is this?

Traditional DAO governance relies on off-chain Snapshot votes, multisig admins, or human committees — all of which are slow, gameable, or require trust. `genlayer-dao` moves governance logic **fully on-chain** with AI consensus:

- **AI-triaged proposals** — LLM validators reject spam and off-topic proposals before they enter voting
- **Rubric-based grant scoring** — validators score applications against defined criteria; top projects auto-receive funds
- **Per-milestone bounty verification** — each deliverable is independently evaluated before payout
- **Constitutional veto** — every governance action is checked against an immutable on-chain constitution before execution
- **No single point of trust** — GenLayer validators reach consensus independently; no admin can override the AI

---

## The 4 Contracts

| Contract | Pattern | Best For |
|---|---|---|
| `dao_proposal.py` | Submit → AI triage → vote → execute | General governance, parameter changes |
| `dao_grant.py` | Apply → AI score rubric → auto-distribute | OSS funding, hackathon prizes, ecosystem grants |
| `dao_bounty.py` | Claim → submit milestones → AI verify each → payout | Development bounties, research tasks |
| `dao_veto.py` | Seal constitution → submit action → AI check → ALLOWED/VETOED | Pre-execution compliance layer |

---

## Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/en/download/)
- **Docker 26+** — [Download](https://docs.docker.com/get-docker/) (only if running local Studio)
- **A funded GenLayer account** — Get test GEN from the [testnet faucet](https://testnet-faucet.genlayer.foundation/)

---

## Installation

```bash
pip install genlayer-dao
```

Also install the linter and GenLayer CLI:

```bash
pip install genvm-linter
npm install -g genlayer
```

---

## Getting the Contract Files

GenLayer contracts run as **single Python files**, so you need to copy them into your project before deploying.

### Recommended (CLI)

After installing the package, run:

```bash
genlayer-dao init
```

This will create a `contracts/` folder with all contracts:

```
contracts/
├── dao_proposal.py
├── dao_grant.py
├── dao_bounty.py
└── dao_veto.py
```

### Copy a single contract

```bash
genlayer-dao proposal
genlayer-dao grant
genlayer-dao bounty
genlayer-dao veto
```

### List available contracts

```bash
genlayer-dao list
```

---

## CLI Usage

| Command | Description |
|---|---|
| `genlayer-dao init` | Copy all 4 contracts |
| `genlayer-dao proposal` | Copy proposal contract |
| `genlayer-dao grant` | Copy grant contract |
| `genlayer-dao bounty` | Copy bounty contract |
| `genlayer-dao veto` | Copy veto contract |
| `genlayer-dao list` | Show available contracts |

---

## Understanding Wei and GEN Units

GenLayer uses **GEN** as its native token, denominated in **wei**:

> **1 GEN = 10¹⁸ wei = 1,000,000,000,000,000,000 wei**

| Amount in GEN | Amount in Wei |
|---|---|
| 0.001 GEN | `1000000000000000` |
| 0.01 GEN | `10000000000000000` |
| 0.1 GEN | `100000000000000000` |
| **1 GEN** | **`1000000000000000000`** |
| 5 GEN | `5000000000000000000` |

> In GenLayer Studio, the Value field auto-multiplies by 10¹⁸. But **constructor arguments** must be entered as full wei values.

---

## Testing Guides

Each contract has a detailed step-by-step testing guide in the `docs/` folder:

| Contract | Guide | Est. Time |
|---|---|---|
| DaoProposal | [docs/test-proposal.md](docs/test-proposal.md) | ~25 min |
| DaoGrant | [docs/test-grant.md](docs/test-grant.md) | ~30 min |
| DaoBounty | [docs/test-bounty.md](docs/test-bounty.md) | ~35 min |
| DaoVeto | [docs/test-veto.md](docs/test-veto.md) | ~20 min |

---

## Deployment

### Method 1: CLI Direct

Set your network first:

```bash
genlayer network set localnet
genlayer network set testnet-bradbury
```

#### Deploy DaoProposal

```bash
genlayer deploy --contract contracts/dao_proposal.py
```

| Argument | Example Value |
|---|---|
| `dao_name` | `MyDAO` |
| `dao_mission` | `Fund and govern open-source AI tooling for the GenLayer ecosystem.` |
| `voting_period_blocks` | `100` |
| `quorum_percent` | `51` |

#### Deploy DaoGrant

```bash
genlayer deploy --contract contracts/dao_grant.py
```

| Argument | Example Value |
|---|---|
| `grant_name` | `Q3 OSS Grant` |
| `grant_purpose` | `Fund open-source developer tools that improve the GenLayer developer experience.` |
| `rubric_impact` | `Does this project meaningfully improve lives or unblock other builders?` |
| `rubric_feasibility` | `Can this team realistically deliver in 3 months given their track record?` |
| `rubric_originality` | `Is this solving a problem that existing tools do not already solve well?` |
| `max_winners` | `3` |

#### Deploy DaoBounty

```bash
genlayer deploy --contract contracts/dao_bounty.py
```

| Argument | Example Value |
|---|---|
| `bounty_title` | `GenLayer Analytics Dashboard` |
| `bounty_description` | `Build a public dashboard showing GenLayer network stats: validator count, tx volume, contract calls.` |
| `milestone_titles_csv` | `Design mockups\|Frontend build\|Deploy and docs` |
| `milestone_criteria_csv` | `Figma file with 5+ screens reviewed\|Functional React app with all charts\|Live URL with README` |
| `milestone_weights_csv` | `20\|60\|20` |
| `arbiter_addr` | `0x0000000000000000000000000000000000000000` |
| `max_dispute_attempts` | `2` |

#### Deploy DaoVeto

```bash
genlayer deploy --contract contracts/dao_veto.py
```

| Argument | Min Length | Example Value |
|---|---|---|
| `dao_name` | 3 chars | `MyDAO` |
| `constitution` | 100 chars | See example below |

Constitution example:
```
1. The DAO may not allocate more than 20% of the treasury in a single vote.
2. No member may hold more than 40% of total voting power.
3. Changes to this constitution require a 80% supermajority.
4. All funded projects must publish their work under an open-source license.
```

### Method 2: GenLayer Studio

1. Open [studio.genlayer.com](https://studio.genlayer.com)
2. Click **Load Contract** → paste contract code
3. Click **Deploy** → fill constructor fields → confirm
4. Copy the contract address

---

## Contract API Reference

### DaoProposal

**Constructor:** `dao_name`, `dao_mission` (≥50 chars), `voting_period_blocks`, `quorum_percent` (1-100)

| Method | Type | Description |
|---|---|---|
| `get_dao_info()` | view | DAO config and stats |
| `get_proposal(id)` | view | Full proposal JSON |
| `get_proposal_state(id)` | view | Current state string |
| `get_voting_power(addr)` | view | Member's voting weight |
| `has_voted(id, addr)` | view | True if already voted |
| `get_proposal_count()` | view | Total proposals |
| `submit_proposal(title, desc, url)` | write | Submit + AI triage |
| `vote(id, support)` | write | Cast YES/NO vote |
| `finalize_proposal(id)` | write | Tally votes after period |
| `execute_proposal(id)` | write | Owner marks EXECUTED |
| `register_member(addr, power)` | write | Owner: add member |
| `remove_member(addr)` | write | Owner: remove member |
| `update_dao_mission(text)` | write | Owner: update mission |

**State flow:** `PENDING → ACTIVE / REJECTED → PASSED / REJECTED → EXECUTED`

---

### DaoGrant

**Constructor:** `grant_name`, `grant_purpose` (≥60 chars), `rubric_impact` (≥30), `rubric_feasibility` (≥30), `rubric_originality` (≥30), `max_winners`

| Method | Type | Description |
|---|---|---|
| `get_grant_info()` | view | Grant config and stats |
| `get_application(id)` | view | Application with score |
| `get_application_score(id)` | view | Raw score (0-30) |
| `get_state()` | view | OPEN/REVIEW/SCORED/DISTRIBUTED |
| `get_rubric()` | view | Full rubric JSON |
| `get_contract_balance()` | view | GEN held by contract |
| `fund_treasury()` | write payable | Owner: deposit GEN |
| `submit_application(title, desc, url)` | write | Apply + AI scoring |
| `close_applications()` | write | Owner: close round |
| `finalize_scoring()` | write | Owner: lock scores |
| `distribute()` | write | Owner: pay top N |
| `withdraw_remainder()` | write | Owner: reclaim dust |

**State flow:** `OPEN → REVIEW → SCORED → DISTRIBUTED`

---

### DaoBounty

**Constructor:** `bounty_title`, `bounty_description` (≥60), `milestone_titles_csv`, `milestone_criteria_csv`, `milestone_weights_csv` (sum=100), `arbiter_addr`, `max_dispute_attempts` (≥2)

| Method | Who | Description |
|---|---|---|
| `get_bounty_info()` | Anyone | Bounty summary JSON |
| `get_milestone(id)` | Anyone | Milestone state + verdict |
| `get_state()` | Anyone | Current bounty state |
| `get_current_milestone()` | Anyone | Which milestone is next |
| `get_dispute_attempts()` | Anyone | Retry count |
| `fund_bounty()` payable | Owner | Add GEN to pool |
| `claim_bounty()` | Anyone | Become hunter |
| `submit_milestone(url, notes)` | Hunter | Submit + AI verify |
| `retry_milestone(url, notes)` | Hunter | Re-submit disputed milestone |
| `owner_approve_milestone()` | Owner | Override AI rejection |
| `arbiter_rule(approve)` | Arbiter | Resolve dispute |
| `force_claim_payout()` | Hunter | Safety valve after max attempts |
| `cancel_bounty()` | Owner | Refund if unclaimed |

**State flow:** `OPEN → CLAIMED → [M0..Mn: PENDING→SUBMITTED→APPROVED] → COMPLETED`

---

### DaoVeto

**Constructor:** `dao_name`, `constitution` (≥100 chars)

| Method | Type | Description |
|---|---|---|
| `get_constitution()` | view | Full constitution text |
| `is_sealed()` | view | True after sealing |
| `get_dao_info()` | view | Stats and config |
| `get_check(id)` | view | Check result JSON |
| `get_check_state(id)` | view | PENDING/ALLOWED/VETOED |
| `is_allowed(id)` | view | True if passed (for downstream contracts) |
| `is_checker(addr)` | view | True if registered |
| `get_stats()` | view | Total allowed/vetoed counts |
| `submit_for_review(title, desc, url)` | write | Submit action for AI veto check |
| `update_constitution(text)` | write | Owner: edit before sealing |
| `seal_constitution()` | write | Owner: lock forever |
| `register_checker(addr)` | write | Owner: authorize checker |
| `remove_checker(addr)` | write | Owner: deauthorize |

**State flow per check:** `PENDING → ALLOWED / VETOED`

---

## Consensus Design

Each contract uses a different consensus strategy, chosen for the risk level of the action:

| Contract | Consensus Method | Why |
|---|---|---|
| `dao_proposal.py` triage | `prompt_comparative` | Triage is soft — validators agree on direction, not exact wording |
| `dao_grant.py` scoring | `prompt_comparative` | Score tier (HIGH/MEDIUM/LOW) must match; exact numbers can vary |
| `dao_bounty.py` milestone | `strict_eq` | Irreversible transfer gate — all validators must return identical verdict |
| `dao_veto.py` check | `prompt_comparative` | Constitution check — validators agree on ALLOWED/VETOED |

---

## Use Case Examples

### AI-Triaged Governance Proposal

```bash
# Deploy
genlayer deploy --contract contracts/dao_proposal.py

# Register members with voting power
genlayer write --address 0xCONTRACT --function register_member \
  --args 0xMEMBER 100

# Submit proposal (triggers AI triage)
genlayer write --address 0xCONTRACT --function submit_proposal \
  --args "Increase validator rewards" \
  "Proposal to increase validator rewards by 15% to attract more node operators to the network." \
  "https://github.com/solana-foundation/solana-improvement-documents/blob/main/proposals/0096-reward-collected-priority-fee-in-entirety.md"

# Vote YES (as registered member)
genlayer write --address 0xCONTRACT --function vote --args 0 true

# Finalize after voting period
genlayer write --address 0xCONTRACT --function finalize_proposal --args 0
```

### AI-Scored Grant Round

```bash
# Deploy + fund treasury
genlayer deploy --contract contracts/dao_grant.py
genlayer write --address 0xCONTRACT --function fund_treasury --value 10000000000000000000

# Applications (triggers AI scoring per submit)
genlayer write --address 0xCONTRACT --function submit_application \
  --args "GenLayer DevKit" \
  "A CLI toolkit that streamlines GenLayer contract development with hot reload, local testing, and type hints." \
  "https://github.com/filecoin-project/devgrants/blob/master/Program%20Resources/Open%20Grants%20README.md"

# Owner closes, finalizes, distributes
genlayer write --address 0xCONTRACT --function close_applications
genlayer write --address 0xCONTRACT --function finalize_scoring
genlayer write --address 0xCONTRACT --function distribute
```

### Constitutional Veto Check

```bash
# Deploy with constitution
genlayer deploy --contract contracts/dao_veto.py

# Seal constitution (irreversible)
genlayer write --address 0xCONTRACT --function seal_constitution

# Register checker (e.g. your proposal contract)
genlayer write --address 0xCONTRACT --function register_checker --args 0xCHECKER

# Submit action for review (as registered checker)
genlayer write --address 0xCONTRACT --function submit_for_review \
  --args "Treasury allocation vote" \
  "Proposal to allocate 25% of treasury to marketing efforts in Q4." \
  "https://github.com/ArbitrumFoundation/governance/blob/main/docs/overview.md"

# Query result
genlayer call --address 0xCONTRACT --function is_allowed --args 0
```

---

## Linting

Before deploying, lint your contracts:

```bash
genvm-lint check contracts/dao_proposal.py
genvm-lint check contracts/dao_grant.py
genvm-lint check contracts/dao_bounty.py
genvm-lint check contracts/dao_veto.py
```

---

## Security Notes

- **Sealed constitutions** — `dao_veto.py` enforces immutability: once `seal_constitution()` is called, the ruleset cannot change, ever.
- **Strict vs comparative consensus** — `dao_bounty.py` uses `strict_eq` for milestone payouts because transfers are irreversible; the others use `prompt_comparative` which is safer for subjective evaluations.
- **Force-release safety valves** — `dao_bounty.py` prevents permanent lockup with `force_claim_payout()` after `max_dispute_attempts`.
- **Owner cannot claim own bounty** — `dao_bounty.py` explicitly blocks the deployer from claiming.
- **Voting power is explicit** — `dao_proposal.py` stores power at registration time; changes don't affect active proposals.

---

## Troubleshooting

**"Constitution must be sealed"** — call `seal_constitution()` on `dao_veto.py` before submitting checks.

**"Milestone weights must sum to 100"** — check your `milestone_weights_csv` adds up to exactly 100.

**"Not a registered member"** — call `register_member(addr, power)` as owner before voting.

**"Grant round is not accepting applications"** — state must be OPEN; check with `get_state()`.

**"Insufficient balance"** — fund the contract first with `fund_treasury()` or `fund_bounty()`.

**Lint fails with relative import error** — contracts must be copied to your local project folder before linting.

**"Insufficient balance" on testnet** — get test GEN from [testnet-faucet.genlayer.foundation](https://testnet-faucet.genlayer.foundation/).

---

## Resources

- 📖 [GenLayer Docs](https://docs.genlayer.com)
- 📘 [GenLayer SDK Reference](https://sdk.genlayer.com)
- 🎮 [GenLayer Studio](https://studio.genlayer.com)
- 🔧 [GenVM Linter Docs](https://docs.genlayer.com/api-references/genlayer-linter)
- 💧 [Testnet Faucet](https://testnet-faucet.genlayer.foundation/)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Contributing

Issues and pull requests welcome!

1. Fork the repo
2. Create a feature branch
3. Commit changes with clear messages
4. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE).
