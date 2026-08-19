# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import typing


class DaoProposal(gl.Contract):
    """
    DaoProposal — AI-triaged governance proposal and voting.

    Workflow:
      1. Anyone submits a proposal with title + description + action URL
      2. GenLayer LLM validators triage the proposal:
         - Is it coherent and non-duplicate?
         - Does it meet the DAO's minimum quality bar?
      3. If ACTIVE, token-weighted members vote YES/NO during voting period
      4. After voting period, tally determines PASSED or REJECTED
      5. Owner executes PASSED proposals

    State flow:
      PENDING -> ACTIVE (passed triage) / REJECTED (failed triage)
      ACTIVE  -> PASSED / REJECTED  (after voting period ends)
      PASSED  -> EXECUTED

    Consensus:
      - Triage: gl.eq_principle.prompt_comparative
        All validators must agree on ACTIVE or REJECTED verdict.
      - Tallying: deterministic (pure arithmetic, no LLM needed).
    """

    # ── DAO CONFIG ────────────────────────────────────────────────
    dao_name: str
    dao_mission: str
    voting_period_blocks: u256
    quorum_percent: u256          # 0-100, min % of total votes needed
    owner: Address

    # ── PROPOSAL STORAGE ─────────────────────────────────────────
    proposal_count: u256
    proposal_titles: TreeMap[u256, str]
    proposal_descriptions: TreeMap[u256, str]
    proposal_action_urls: TreeMap[u256, str]
    proposal_proposers: TreeMap[u256, Address]
    proposal_states: TreeMap[u256, str]
    proposal_ai_verdicts: TreeMap[u256, str]
    proposal_yes_votes: TreeMap[u256, u256]
    proposal_no_votes: TreeMap[u256, u256]
    proposal_created_at: TreeMap[u256, u256]

    # ── VOTING RECORDS ────────────────────────────────────────────
    # key: proposal_id * 10^40 + voter_address_int (simplified: store as str key)
    votes_cast: TreeMap[str, u256]   # "pid:addr" -> 1 = voted

    # ── MEMBER REGISTRY ───────────────────────────────────────────
    voting_power: TreeMap[Address, u256]
    total_voting_power: u256
    member_count: u256

    def __init__(
        self,
        dao_name: str,
        dao_mission: str,
        voting_period_blocks: u256,
        quorum_percent: u256,
    ):
        """
        Initialize the DAO governance contract.

        Args:
            dao_name             (str):   Name of the DAO
            dao_mission          (str):   Mission statement used by AI triage (>= 50 chars)
            voting_period_blocks (u256):  How many blocks a proposal stays open for votes
            quorum_percent       (u256):  Min % of total voting power required (1-100)
        """
        assert len(dao_name) >= 3, "DAO name must be at least 3 characters"
        assert len(dao_mission) >= 50, "DAO mission must be at least 50 characters"
        assert voting_period_blocks >= u256(1), "Voting period must be at least 1 block"
        assert quorum_percent >= u256(1) and quorum_percent <= u256(100), \
            "Quorum percent must be between 1 and 100"

        self.dao_name = dao_name
        self.dao_mission = dao_mission
        self.voting_period_blocks = voting_period_blocks
        self.quorum_percent = quorum_percent
        self.owner = gl.message.sender_address
        self.proposal_count = u256(0)
        self.total_voting_power = u256(0)
        self.member_count = u256(0)

    # ── VIEW METHODS ──────────────────────────────────────────────

    @gl.public.view
    def get_dao_info(self) -> str:
        return (
            '{"name": "' + self.dao_name.replace('"', "'") +
            '", "mission": "' + self.dao_mission.replace('"', "'") +
            '", "voting_period_blocks": ' + str(self.voting_period_blocks) +
            ', "quorum_percent": ' + str(self.quorum_percent) +
            ', "proposal_count": ' + str(self.proposal_count) +
            ', "member_count": ' + str(self.member_count) +
            ', "total_voting_power": ' + str(self.total_voting_power) + '}'
        )

    @gl.public.view
    def get_proposal(self, proposal_id: u256) -> str:
        assert proposal_id < self.proposal_count, "dao: Invalid proposal ID"
        return (
            '{"id": ' + str(proposal_id) +
            ', "title": "' + self.proposal_titles.get(proposal_id, "").replace('"', "'") +
            '", "description": "' + self.proposal_descriptions.get(proposal_id, "").replace('"', "'") +
            '", "action_url": "' + self.proposal_action_urls.get(proposal_id, "") +
            '", "state": "' + self.proposal_states.get(proposal_id, "") +
            '", "yes_votes": ' + str(self.proposal_yes_votes.get(proposal_id, u256(0))) +
            ', "no_votes": ' + str(self.proposal_no_votes.get(proposal_id, u256(0))) +
            ', "ai_verdict": "' + self.proposal_ai_verdicts.get(proposal_id, "").replace('"', "'") +
            '"}'
        )

    @gl.public.view
    def get_proposal_state(self, proposal_id: u256) -> str:
        assert proposal_id < self.proposal_count, "dao: Invalid proposal ID"
        return self.proposal_states.get(proposal_id, "")

    @gl.public.view
    def get_voting_power(self, member_address: str) -> u256:
        member = Address(member_address)
        return self.voting_power.get(member, u256(0))

    @gl.public.view
    def has_voted(self, proposal_id: u256, voter_address: str) -> bool:
        key = str(proposal_id) + ":" + voter_address
        return self.votes_cast.get(key, u256(0)) > u256(0)

    @gl.public.view
    def get_proposal_count(self) -> u256:
        return self.proposal_count

    @gl.public.view
    def get_member_count(self) -> u256:
        return self.member_count

    @gl.public.view
    def get_total_voting_power(self) -> u256:
        return self.total_voting_power

    # ── WRITE METHODS ─────────────────────────────────────────────

    @gl.public.write
    def submit_proposal(
        self,
        title: str,
        description: str,
        action_url: str,
    ) -> typing.Any:
        """
        Submit a governance proposal. Triggers AI triage immediately.

        Consensus (prompt_comparative):
          Each GenLayer validator independently evaluates whether the
          proposal is coherent, relevant to the DAO mission, and not a
          duplicate or spam. All validators must agree on ACTIVE or
          REJECTED before the state is committed on-chain.

        Args:
            title       (str): Proposal title (>= 10 chars)
            description (str): Detailed description (>= 80 chars)
            action_url  (str): URL to supporting doc, code, or spec
        """
        assert len(title) >= 10, "dao: Title must be at least 10 characters"
        assert len(description) >= 80, "dao: Description must be at least 80 characters"
        assert len(action_url) > 0, "dao: Action URL required"

        pid = self.proposal_count
        self.proposal_count = self.proposal_count + u256(1)

        self.proposal_titles[pid] = title
        self.proposal_descriptions[pid] = description
        self.proposal_action_urls[pid] = action_url
        self.proposal_proposers[pid] = gl.message.sender_address
        self.proposal_states[pid] = "PENDING"
        self.proposal_yes_votes[pid] = u256(0)
        self.proposal_no_votes[pid] = u256(0)

        def nondet() -> str:
            fetched = ""
            if len(action_url) > 0:
                try:
                    response = gl.nondet.web.get(action_url)
                    raw = response.body.decode("utf-8")
                    fetched = raw[:1500] if len(raw) > 1500 else raw
                except Exception:
                    fetched = "[Could not fetch URL]"

            task = (
                "You are a governance AI for a DAO. Your job is to triage proposals.\n\n"
                "=== DAO MISSION ===\n" + self.dao_mission + "\n\n"
                "=== PROPOSAL ===\n"
                "Title: " + title + "\n"
                "Description: " + description + "\n"
                "Action URL content (fetched):\n" + fetched + "\n\n"
                "=== YOUR TASK ===\n"
                "Is this proposal:\n"
                "1. Coherent and clearly written?\n"
                "2. Relevant to the DAO mission?\n"
                "3. Specific enough to be actionable?\n"
                "4. Not obvious spam or a duplicate concept?\n\n"
                "Respond with ONLY 'ACTIVE' or 'REJECTED' as the first word, "
                "followed by a single-sentence reason."
            )
            return gl.nondet.exec_prompt(task)

        verdict = gl.eq_principle.prompt_comparative(
            nondet,
            "The verdicts must reach the same ACTIVE or REJECTED conclusion"
        )

        self.proposal_ai_verdicts[pid] = verdict

        if verdict.strip().startswith("ACTIVE"):
            self.proposal_states[pid] = "ACTIVE"
        else:
            self.proposal_states[pid] = "REJECTED"

        return verdict

    @gl.public.write
    def vote(self, proposal_id: u256, support: bool) -> None:
        """
        Cast a YES or NO vote on an ACTIVE proposal.
        Voting power is determined by the member's registered weight.

        Args:
            proposal_id (u256): Proposal to vote on
            support     (bool): True = YES, False = NO
        """
        assert proposal_id < self.proposal_count, "dao: Invalid proposal ID"
        assert self.proposal_states.get(proposal_id, "") == "ACTIVE", \
            "dao: Proposal is not in ACTIVE state"

        sender = gl.message.sender_address
        power = self.voting_power.get(sender, u256(0))
        assert power > u256(0), "dao: Not a registered member with voting power"

        vote_key = str(proposal_id) + ":" + sender.as_hex
        assert self.votes_cast.get(vote_key, u256(0)) == u256(0), \
            "dao: Already voted on this proposal"

        self.votes_cast[vote_key] = u256(1)

        if support:
            current = self.proposal_yes_votes.get(proposal_id, u256(0))
            self.proposal_yes_votes[proposal_id] = current + power
        else:
            current = self.proposal_no_votes.get(proposal_id, u256(0))
            self.proposal_no_votes[proposal_id] = current + power

    @gl.public.write
    def finalize_proposal(self, proposal_id: u256) -> str:
        """
        Finalize an ACTIVE proposal after the voting period.
        Tallies YES/NO votes and checks quorum. Deterministic — no LLM.

        State transition: ACTIVE -> PASSED or REJECTED
        """
        assert proposal_id < self.proposal_count, "dao: Invalid proposal ID"
        assert self.proposal_states.get(proposal_id, "") == "ACTIVE", \
            "dao: Proposal is not ACTIVE"

        yes = self.proposal_yes_votes.get(proposal_id, u256(0))
        no = self.proposal_no_votes.get(proposal_id, u256(0))
        total_cast = yes + no

        # Check quorum: total votes cast must be >= quorum_percent of total_voting_power
        quorum_required = (self.total_voting_power * self.quorum_percent) // u256(100)
        if total_cast < quorum_required:
            self.proposal_states[proposal_id] = "REJECTED"
            return "REJECTED: quorum not reached"

        if yes > no:
            self.proposal_states[proposal_id] = "PASSED"
            return "PASSED"
        else:
            self.proposal_states[proposal_id] = "REJECTED"
            return "REJECTED: more NO votes than YES"

    @gl.public.write
    def execute_proposal(self, proposal_id: u256) -> None:
        """
        Mark a PASSED proposal as EXECUTED. Owner only.
        Off-chain execution (governance action) is separate.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can execute"
        assert proposal_id < self.proposal_count, "dao: Invalid proposal ID"
        assert self.proposal_states.get(proposal_id, "") == "PASSED", \
            "dao: Proposal is not PASSED"

        self.proposal_states[proposal_id] = "EXECUTED"

    # ── MEMBER MANAGEMENT ─────────────────────────────────────────

    @gl.public.write
    def register_member(self, member_address: str, power: u256) -> None:
        """
        Register or update a member's voting power. Owner only.

        Args:
            member_address (str):   Hex address of the member
            power          (u256):  Voting weight (e.g. 1 = 1 token)
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can register members"
        assert power > u256(0), "dao: Voting power must be > 0"

        member = Address(member_address)
        current_power = self.voting_power.get(member, u256(0))

        if current_power == u256(0):
            self.member_count = self.member_count + u256(1)

        self.total_voting_power = self.total_voting_power - current_power + power
        self.voting_power[member] = power

    @gl.public.write
    def remove_member(self, member_address: str) -> None:
        """Remove a member and subtract their voting power. Owner only."""
        assert gl.message.sender_address == self.owner, "dao: Only owner can remove members"

        member = Address(member_address)
        current_power = self.voting_power.get(member, u256(0))
        assert current_power > u256(0), "dao: Member not registered"

        self.voting_power[member] = u256(0)
        self.total_voting_power = self.total_voting_power - current_power
        self.member_count = self.member_count - u256(1)

    @gl.public.write
    def update_dao_mission(self, new_mission: str) -> None:
        """Update DAO mission used in AI triage. Owner only."""
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert len(new_mission) >= 50, "dao: Mission must be at least 50 characters"
        self.dao_mission = new_mission
