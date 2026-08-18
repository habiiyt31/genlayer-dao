# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import typing


class DaoBounty(gl.Contract):
    """
    DaoBounty — Multi-milestone DAO bounty with per-milestone AI verification.

    Workflow:
      1. Owner deploys with a list of milestones encoded as a structured brief
      2. Anyone claims the bounty (first claimant wins)
      3. Hunter submits each milestone's deliverable URL one by one
      4. GenLayer LLM validators verify each milestone independently
      5. Each approved milestone releases its proportional share of the bounty
      6. If all milestones approved -> COMPLETED

    State flow:
      OPEN -> CLAIMED -> [M0_SUBMITTED -> M0_APPROVED, M1_SUBMITTED -> ...] -> COMPLETED
      At any point: DISPUTED (if validator rejects + no arbiter override)

    Consensus:
      gl.eq_principle.strict_eq — all validators must return the exact same
      APPROVED or REJECTED verdict for each milestone. This is stricter than
      proposal triage because milestone payouts are irreversible transfers.
    """

    # ── CONFIG ────────────────────────────────────────────────────
    bounty_title: str
    bounty_description: str
    owner: Address
    arbiter: Address
    max_dispute_attempts: u256

    # ── MILESTONE STORAGE ─────────────────────────────────────────
    milestone_count: u256
    milestone_titles: TreeMap[u256, str]
    milestone_criteria: TreeMap[u256, str]
    milestone_weights: TreeMap[u256, u256]   # percentage of total (must sum to 100)
    milestone_states: TreeMap[u256, str]     # PENDING | SUBMITTED | APPROVED | DISPUTED
    milestone_urls: TreeMap[u256, str]
    milestone_verdicts: TreeMap[u256, str]

    # ── BOUNTY STATE ──────────────────────────────────────────────
    state: str
    total_amount: u256
    hunter: Address
    milestones_approved: u256
    dispute_attempts: u256
    current_milestone: u256      # which milestone is active for submission

    def __init__(
        self,
        bounty_title: str,
        bounty_description: str,
        milestone_titles_csv: str,
        milestone_criteria_csv: str,
        milestone_weights_csv: str,
        arbiter_addr: str,
        max_dispute_attempts: u256,
    ):
        """
        Initialize a multi-milestone bounty.

        Args:
            bounty_title           (str):   Title of the bounty (>= 10 chars)
            bounty_description     (str):   Overall description (>= 60 chars)
            milestone_titles_csv   (str):   Pipe-separated milestone titles e.g. "Design|Build|Test"
            milestone_criteria_csv (str):   Pipe-separated acceptance criteria per milestone
            milestone_weights_csv  (str):   Pipe-separated integer weights summing to 100 e.g. "30|50|20"
            arbiter_addr           (str):   Hex address of neutral arbiter (use zero address if none)
            max_dispute_attempts   (u256):  Min 2 — attempts before force-claim unlocks
        """
        assert len(bounty_title) >= 10, "Bounty title must be at least 10 characters"
        assert len(bounty_description) >= 60, "Bounty description must be at least 60 characters"
        assert max_dispute_attempts >= u256(2), "Max dispute attempts must be at least 2"

        titles = milestone_titles_csv.split("|")
        criteria = milestone_criteria_csv.split("|")
        weights_str = milestone_weights_csv.split("|")

        assert len(titles) >= 2, "Must have at least 2 milestones"
        assert len(titles) == len(criteria), "Milestone titles and criteria count must match"
        assert len(titles) == len(weights_str), "Milestone titles and weights count must match"
        assert len(titles) <= 10, "Maximum 10 milestones"

        weight_sum = 0
        for w in weights_str:
            weight_sum += int(w.strip())
        assert weight_sum == 100, "Milestone weights must sum to 100"

        self.bounty_title = bounty_title
        self.bounty_description = bounty_description
        self.owner = gl.message.sender_address
        self.arbiter = Address(arbiter_addr)
        self.max_dispute_attempts = max_dispute_attempts
        self.state = "OPEN"
        self.total_amount = u256(0)
        self.hunter = Address("0x0000000000000000000000000000000000000000")
        self.milestones_approved = u256(0)
        self.dispute_attempts = u256(0)
        self.current_milestone = u256(0)

        count = len(titles)
        self.milestone_count = u256(count)

        for i in range(count):
            idx = u256(i)
            t = titles[i].strip()
            c = criteria[i].strip()
            w = int(weights_str[i].strip())
            assert len(t) >= 3, "Each milestone title must be at least 3 characters"
            assert len(c) >= 20, "Each milestone criteria must be at least 20 characters"
            assert w >= 1, "Each milestone weight must be at least 1"
            self.milestone_titles[idx] = t
            self.milestone_criteria[idx] = c
            self.milestone_weights[idx] = u256(w)
            self.milestone_states[idx] = "PENDING"
            self.milestone_urls[idx] = ""
            self.milestone_verdicts[idx] = ""

    # ── VIEW METHODS ──────────────────────────────────────────────

    @gl.public.view
    def get_bounty_info(self) -> str:
        return (
            '{"title": "' + self.bounty_title.replace('"', "'") +
            '", "description": "' + self.bounty_description.replace('"', "'") +
            '", "state": "' + self.state +
            '", "total_amount_wei": ' + str(self.total_amount) +
            ', "hunter": "' + self.hunter.as_hex +
            '", "milestone_count": ' + str(self.milestone_count) +
            ', "milestones_approved": ' + str(self.milestones_approved) +
            ', "current_milestone": ' + str(self.current_milestone) + '}'
        )

    @gl.public.view
    def get_milestone(self, milestone_id: u256) -> str:
        assert milestone_id < self.milestone_count, "dao: Invalid milestone ID"
        return (
            '{"id": ' + str(milestone_id) +
            ', "title": "' + self.milestone_titles.get(milestone_id, "").replace('"', "'") +
            '", "criteria": "' + self.milestone_criteria.get(milestone_id, "").replace('"', "'") +
            '", "weight_percent": ' + str(self.milestone_weights.get(milestone_id, u256(0))) +
            ', "state": "' + self.milestone_states.get(milestone_id, "") +
            '", "url": "' + self.milestone_urls.get(milestone_id, "") +
            '", "verdict": "' + self.milestone_verdicts.get(milestone_id, "").replace('"', "'") +
            '"}'
        )

    @gl.public.view
    def get_state(self) -> str:
        return self.state

    @gl.public.view
    def get_current_milestone(self) -> u256:
        return self.current_milestone

    @gl.public.view
    def get_milestone_count(self) -> u256:
        return self.milestone_count

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

    @gl.public.view
    def get_dispute_attempts(self) -> u256:
        return self.dispute_attempts

    # ── WRITE METHODS ─────────────────────────────────────────────

    @gl.public.write.payable
    def fund_bounty(self) -> None:
        """
        Owner funds the bounty with GEN. Can top up multiple times while OPEN.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can fund"
        assert self.state == "OPEN", "dao: Can only fund in OPEN state"
        assert gl.message.value > u256(0), "dao: Must send GEN to fund"

        self.total_amount = self.total_amount + gl.message.value

    @gl.public.write
    def claim_bounty(self) -> None:
        """
        First caller claims the bounty and becomes the hunter.
        Transitions OPEN -> CLAIMED.
        Owner cannot claim their own bounty.
        """
        assert self.state == "OPEN", "dao: Bounty not open for claiming"
        assert self.total_amount > u256(0), "dao: Bounty not yet funded"
        assert gl.message.sender_address != self.owner, "dao: Owner cannot claim own bounty"

        self.hunter = gl.message.sender_address
        self.state = "CLAIMED"

    @gl.public.write
    def submit_milestone(self, deliverable_url: str, notes: str) -> typing.Any:
        """
        Hunter submits a milestone deliverable URL.
        Triggers AI verification via GenLayer validators.

        Consensus (strict_eq):
          All validators independently fetch the deliverable URL and
          evaluate it against the milestone's acceptance criteria.
          They must return the EXACT same verdict string — APPROVED or
          REJECTED — before the result is committed. This is stricter
          than prompt_comparative because it's a binary transfer gate.

        Args:
            deliverable_url (str): URL to the milestone deliverable
            notes           (str): Hunter's notes on the submission
        """
        assert self.state == "CLAIMED", "dao: Bounty not in CLAIMED state"
        assert gl.message.sender_address == self.hunter, "dao: Only hunter can submit"
        assert len(deliverable_url) > 0, "dao: Deliverable URL required"

        mid = self.current_milestone
        assert mid < self.milestone_count, "dao: All milestones already submitted"
        assert self.milestone_states.get(mid, "") == "PENDING", \
            "dao: This milestone already submitted"

        self.milestone_urls[mid] = deliverable_url
        self.milestone_states[mid] = "SUBMITTED"

        m_title = self.milestone_titles.get(mid, "")
        m_criteria = self.milestone_criteria.get(mid, "")

        def nondet() -> str:
            content = ""
            try:
                response = gl.nondet.web.get(deliverable_url)
                raw = response.body.decode("utf-8")
                content = raw[:2500] if len(raw) > 2500 else raw
            except Exception:
                content = "[Could not fetch deliverable URL]"

            task = (
                "You are verifying a bounty milestone deliverable.\n\n"
                "=== BOUNTY ===\n"
                "Title: " + self.bounty_title + "\n"
                "Description: " + self.bounty_description + "\n\n"
                "=== MILESTONE " + str(mid) + " ===\n"
                "Title: " + m_title + "\n"
                "Acceptance Criteria: " + m_criteria + "\n\n"
                "=== SUBMISSION ===\n"
                "Hunter notes: " + notes + "\n"
                "Deliverable content (fetched from URL):\n" + content + "\n\n"
                "=== YOUR TASK ===\n"
                "Does this submission meet ALL acceptance criteria for this milestone?\n"
                "Be strict. Partial completion is REJECTED.\n"
                "Respond with ONLY 'APPROVED' or 'REJECTED' as the first word, "
                "followed by a single-sentence reason."
            )
            return gl.nondet.exec_prompt(task)

        verdict = gl.eq_principle.strict_eq(nondet)

        self.milestone_verdicts[mid] = verdict

        if verdict.strip().startswith("APPROVED"):
            self.milestone_states[mid] = "APPROVED"
            self.milestones_approved = self.milestones_approved + u256(1)

            # Pay this milestone's share immediately
            weight = self.milestone_weights.get(mid, u256(0))
            payout = (self.total_amount * weight) // u256(100)

            if payout > u256(0) and payout <= self.balance:
                @gl.evm.contract_interface
                class _EOA:
                    class View:
                        pass
                    class Write:
                        pass

                _EOA(self.hunter).emit_transfer(value=payout)

            # Advance to next milestone
            self.current_milestone = mid + u256(1)
            self.dispute_attempts = u256(0)

            # Check if all milestones done
            if self.milestones_approved >= self.milestone_count:
                self.state = "COMPLETED"
        else:
            self.milestone_states[mid] = "DISPUTED"
            self.state = "DISPUTED"

        return verdict

    @gl.public.write
    def retry_milestone(self, new_url: str, notes: str) -> typing.Any:
        """
        Hunter re-submits a DISPUTED milestone with a new deliverable.
        Resets the milestone back to SUBMITTED and re-triggers AI verification.

        Args:
            new_url (str): New deliverable URL
            notes   (str): Updated notes
        """
        assert self.state == "DISPUTED", "dao: Not in DISPUTED state"
        assert gl.message.sender_address == self.hunter, "dao: Only hunter can retry"
        assert len(new_url) > 0, "dao: New URL required"

        mid = self.current_milestone
        self.milestone_urls[mid] = new_url
        self.milestone_states[mid] = "PENDING"
        self.state = "CLAIMED"
        self.dispute_attempts = self.dispute_attempts + u256(1)

        return self.submit_milestone(new_url, notes)

    @gl.public.write
    def owner_approve_milestone(self) -> None:
        """
        Owner manually approves a DISPUTED milestone (override AI verdict).
        Releases the milestone payout and advances to next milestone.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can approve"
        assert self.state == "DISPUTED", "dao: Not in DISPUTED state"

        mid = self.current_milestone
        self.milestone_states[mid] = "APPROVED"
        self.milestones_approved = self.milestones_approved + u256(1)
        verdict_update = self.milestone_verdicts.get(mid, "") + " [MANUALLY APPROVED BY OWNER]"
        self.milestone_verdicts[mid] = verdict_update

        weight = self.milestone_weights.get(mid, u256(0))
        payout = (self.total_amount * weight) // u256(100)

        if payout > u256(0) and payout <= self.balance:
            @gl.evm.contract_interface
            class _EOA:
                class View:
                    pass
                class Write:
                    pass

            _EOA(self.hunter).emit_transfer(value=payout)

        self.current_milestone = mid + u256(1)
        self.dispute_attempts = u256(0)

        if self.milestones_approved >= self.milestone_count:
            self.state = "COMPLETED"
        else:
            self.state = "CLAIMED"

    @gl.public.write
    def arbiter_rule(self, approve: bool) -> None:
        """
        Neutral arbiter resolves a disputed milestone.
        approve=True: release payout + advance
        approve=False: reset milestone for hunter to retry
        """
        assert gl.message.sender_address == self.arbiter, "dao: Only arbiter can rule"
        assert self.state == "DISPUTED", "dao: Not in DISPUTED state"

        mid = self.current_milestone
        self.milestone_verdicts[mid] = self.milestone_verdicts.get(mid, "") + " [ARBITER RULED]"

        if approve:
            self.milestone_states[mid] = "APPROVED"
            self.milestones_approved = self.milestones_approved + u256(1)

            weight = self.milestone_weights.get(mid, u256(0))
            payout = (self.total_amount * weight) // u256(100)

            if payout > u256(0) and payout <= self.balance:
                @gl.evm.contract_interface
                class _EOA:
                    class View:
                        pass
                    class Write:
                        pass

                _EOA(self.hunter).emit_transfer(value=payout)

            self.current_milestone = mid + u256(1)
            self.dispute_attempts = u256(0)

            if self.milestones_approved >= self.milestone_count:
                self.state = "COMPLETED"
            else:
                self.state = "CLAIMED"
        else:
            # Reset for re-attempt
            self.milestone_states[mid] = "PENDING"
            self.state = "CLAIMED"

    @gl.public.write
    def force_claim_payout(self) -> None:
        """
        Safety valve: after max_dispute_attempts on one milestone,
        hunter can force-release remaining balance.
        Prevents permanent fund lockup if owner/arbiter go offline.
        """
        assert gl.message.sender_address == self.hunter, "dao: Only hunter can force claim"
        assert self.state == "DISPUTED", "dao: Not in DISPUTED state"
        assert self.dispute_attempts >= self.max_dispute_attempts, \
            "dao: Not enough dispute attempts. Current: " + str(self.dispute_attempts) + \
            ", required: " + str(self.max_dispute_attempts)

        self.state = "COMPLETED"
        mid = self.current_milestone
        self.milestone_verdicts[mid] = self.milestone_verdicts.get(mid, "") + \
            " [FORCE-RELEASED AFTER " + str(self.dispute_attempts) + " ATTEMPTS]"

        if self.balance > u256(0):
            amount = self.balance

            @gl.evm.contract_interface
            class _EOA:
                class View:
                    pass
                class Write:
                    pass

            _EOA(self.hunter).emit_transfer(value=amount)

    @gl.public.write
    def cancel_bounty(self) -> None:
        """
        Cancel an unclaimed bounty and refund treasury. Owner only.
        Can only cancel in OPEN state (before anyone claims).
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can cancel"
        assert self.state == "OPEN", "dao: Can only cancel in OPEN state"

        self.state = "COMPLETED"

        if self.balance > u256(0):
            amount = self.balance

            @gl.evm.contract_interface
            class _EOA:
                class View:
                    pass
                class Write:
                    pass

            _EOA(self.owner).emit_transfer(value=amount)
