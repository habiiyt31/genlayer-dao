# Changelog

## [0.1.1] - 2026-08-18

### Fixed
- `dao_grant.py`: Fixed `distribute()` — replaced local `TreeMap()` (unsupported in GenVM)
  with on-chain `app_is_winner: TreeMap[u256, u256]` field for winner tracking
- `dao_bounty.py`: Removed `emit_transfer` (unsupported in GenVM) — replaced with
  `hunter_earned: u256` on-chain ledger + `withdraw_payout()` pattern
- `dao_bounty.py`: Added `get_hunter_earned()` view method

## [0.1.0] - 2026-08-17

### Added
- `dao_proposal.py` — AI-triaged governance proposal and voting
- `dao_grant.py` — AI-scored grant allocator with rubric-based evaluation
- `dao_bounty.py` — Multi-milestone bounty with per-milestone AI verification
- `dao_veto.py` — Constitutional AI veto for governance actions
- CLI: `genlayer-dao init / proposal / grant / bounty / veto / list`
- Testing guides for all 4 contracts in `docs/`
