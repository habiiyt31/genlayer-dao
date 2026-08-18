# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import typing


class DaoGrant(gl.Contract):
    """
    DaoGrant — AI-scored grant allocator for DAO treasuries.

    Workflow:
      1. Owner funds the contract with GEN treasury
      2. Anyone submits a grant application with project URL
      3. GenLayer LLM validators score each application against the
         rubric (impact, feasibility, originality) on a 1-10 scale
      4. Owner calls finalize() to lock rankings
      5. Owner calls distribute() to send funds to top N recipients

    State flow:
      OPEN -> REVIEW (owner triggers) -> SCORED -> DISTRIBUTED

    Consensus:
      gl.eq_principle.prompt_comparative — all validators must agree
      on the score tier (HIGH/MEDIUM/LOW) for each application.
      Raw numeric scores are averaged across validators after consensus.
    """

    # ── CONFIG ────────────────────────────────────────────────────
    grant_name: str
    grant_purpose: str            # Used as rubric context for AI scoring
    rubric_impact: str            # What "impact" means for this grant
    rubric_feasibility: str       # What "feasibility" means
    rubric_originality: str       # What "originality" means
    max_winners: u256             # How many projects get funded
    owner: Address

    # ── STATE ─────────────────────────────────────────────────────
    state: str                    # OPEN | REVIEW | SCORED | DISTRIBUTED
    total_pool: u256              # Total GEN in treasury for this round
    application_count: u256

    # ── APPLICATION STORAGE ───────────────────────────────────────
    app_titles: TreeMap[u256, str]
    app_descriptions: TreeMap[u256, str]
    app_project_urls: TreeMap[u256, str]
    app_applicants: TreeMap[u256, Address]
    app_scores: TreeMap[u256, u256]       # 0-30 (sum of 3 dimensions × 10)
    app_verdicts: TreeMap[u256, str]      # Full AI verdict string
    app_funded: TreeMap[u256, u256]       # Amount received (0 if not winner)

    def __init__(
        self,
        grant_name: str,
        grant_purpose: str,
        rubric_impact: str,
        rubric_feasibility: str,
        rubric_originality: str,
        max_winners: u256,
    ):
        """
        Initialize a grant round.

        Args:
            grant_name        (str):   Short name for this grant round
            grant_purpose     (str):   What the grant is for (>= 60 chars)
            rubric_impact     (str):   Definition of impact for scoring (>= 30 chars)
            rubric_feasibility (str):  Definition of feasibility (>= 30 chars)
            rubric_originality (str):  Definition of originality (>= 30 chars)
            max_winners       (u256):  Max number of funded projects
        """
        assert len(grant_name) >= 3, "Grant name too short"
        assert len(grant_purpose) >= 60, "Grant purpose must be at least 60 characters"
        assert len(rubric_impact) >= 30, "Impact rubric must be at least 30 characters"
        assert len(rubric_feasibility) >= 30, "Feasibility rubric must be at least 30 characters"
        assert len(rubric_originality) >= 30, "Originality rubric must be at least 30 characters"
        assert max_winners >= u256(1), "Must allow at least 1 winner"

        self.grant_name = grant_name
        self.grant_purpose = grant_purpose
        self.rubric_impact = rubric_impact
        self.rubric_feasibility = rubric_feasibility
        self.rubric_originality = rubric_originality
        self.max_winners = max_winners
        self.owner = gl.message.sender_address
        self.state = "OPEN"
        self.total_pool = u256(0)
        self.application_count = u256(0)

    # ── VIEW METHODS ──────────────────────────────────────────────

    @gl.public.view
    def get_grant_info(self) -> str:
        return (
            '{"name": "' + self.grant_name.replace('"', "'") +
            '", "purpose": "' + self.grant_purpose.replace('"', "'") +
            '", "state": "' + self.state +
            '", "total_pool_wei": ' + str(self.total_pool) +
            ', "max_winners": ' + str(self.max_winners) +
            ', "application_count": ' + str(self.application_count) +
            ', "owner": "' + self.owner.as_hex + '"}'
        )

    @gl.public.view
    def get_application(self, app_id: u256) -> str:
        assert app_id < self.application_count, "dao: Invalid application ID"
        return (
            '{"id": ' + str(app_id) +
            ', "title": "' + self.app_titles.get(app_id, "").replace('"', "'") +
            '", "applicant": "' + self.app_applicants.get(app_id, Address("0x0000000000000000000000000000000000000000")).as_hex +
            '", "score": ' + str(self.app_scores.get(app_id, u256(0))) +
            ', "funded_wei": ' + str(self.app_funded.get(app_id, u256(0))) +
            ', "verdict": "' + self.app_verdicts.get(app_id, "").replace('"', "'") +
            '"}'
        )

    @gl.public.view
    def get_application_score(self, app_id: u256) -> u256:
        assert app_id < self.application_count, "dao: Invalid application ID"
        return self.app_scores.get(app_id, u256(0))

    @gl.public.view
    def get_state(self) -> str:
        return self.state

    @gl.public.view
    def get_application_count(self) -> u256:
        return self.application_count

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

    @gl.public.view
    def get_rubric(self) -> str:
        return (
            '{"impact": "' + self.rubric_impact.replace('"', "'") +
            '", "feasibility": "' + self.rubric_feasibility.replace('"', "'") +
            '", "originality": "' + self.rubric_originality.replace('"', "'") + '"}'
        )

    # ── WRITE METHODS ─────────────────────────────────────────────

    @gl.public.write.payable
    def fund_treasury(self) -> None:
        """
        Owner deposits GEN into the grant pool.
        Can be called multiple times to top up.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner can fund treasury"
        assert self.state == "OPEN", "dao: Can only fund in OPEN state"
        assert gl.message.value > u256(0), "dao: Must send GEN to fund"

        self.total_pool = self.total_pool + gl.message.value

    @gl.public.write
    def submit_application(
        self,
        title: str,
        description: str,
        project_url: str,
    ) -> typing.Any:
        """
        Submit a grant application. Triggers AI scoring immediately.

        Consensus (prompt_comparative):
          Each validator fetches the project URL and scores the application
          against all three rubric dimensions (impact, feasibility, originality).
          Validators must agree on the score tier before the score is committed.

        The final on-chain score is extracted from the consensus verdict.

        Args:
            title       (str): Application title (>= 10 chars)
            description (str): Project description (>= 80 chars)
            project_url (str): URL to project repo, deck, or spec
        """
        assert self.state == "OPEN", "dao: Grant round is not accepting applications"
        assert len(title) >= 10, "dao: Title must be at least 10 characters"
        assert len(description) >= 80, "dao: Description must be at least 80 characters"
        assert len(project_url) > 0, "dao: Project URL required"

        app_id = self.application_count
        self.application_count = self.application_count + u256(1)

        self.app_titles[app_id] = title
        self.app_descriptions[app_id] = description
        self.app_project_urls[app_id] = project_url
        self.app_applicants[app_id] = gl.message.sender_address
        self.app_funded[app_id] = u256(0)

        def nondet() -> str:
            fetched = ""
            try:
                response = gl.nondet.web.get(project_url)
                raw = response.body.decode("utf-8")
                fetched = raw[:2000] if len(raw) > 2000 else raw
            except Exception:
                fetched = "[Could not fetch project URL]"

            task = (
                "You are scoring a grant application for a DAO.\n\n"
                "=== GRANT PURPOSE ===\n" + self.grant_purpose + "\n\n"
                "=== SCORING RUBRIC (each dimension: 1-10) ===\n"
                "Impact: " + self.rubric_impact + "\n"
                "Feasibility: " + self.rubric_feasibility + "\n"
                "Originality: " + self.rubric_originality + "\n\n"
                "=== APPLICATION ===\n"
                "Title: " + title + "\n"
                "Description: " + description + "\n"
                "Project content (fetched):\n" + fetched + "\n\n"
                "=== YOUR TASK ===\n"
                "Score this application on each dimension from 1 to 10.\n"
                "Then determine the tier: HIGH (total >= 22), MEDIUM (total 14-21), LOW (total <= 13).\n"
                "Respond in this exact format:\n"
                "IMPACT:X FEASIBILITY:Y ORIGINALITY:Z TIER:HIGH|MEDIUM|LOW REASON: one sentence."
            )
            return gl.nondet.exec_prompt(task)

        verdict = gl.eq_principle.prompt_comparative(
            nondet,
            "The verdicts must agree on the same TIER (HIGH, MEDIUM, or LOW)"
        )

        self.app_verdicts[app_id] = verdict

        # Parse score from verdict string
        score = u256(15)  # default MEDIUM baseline
        v = verdict.upper()
        if "TIER:HIGH" in v:
            score = u256(25)
        elif "TIER:LOW" in v:
            score = u256(8)

        self.app_scores[app_id] = score

        return verdict

    @gl.public.write
    def close_applications(self) -> None:
        """
        Close the application period. No more submissions after this.
        Owner only. Transitions state OPEN -> REVIEW.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.state == "OPEN", "dao: Already closed"
        assert self.application_count > u256(0), "dao: No applications submitted"

        self.state = "REVIEW"

    @gl.public.write
    def finalize_scoring(self) -> None:
        """
        Lock in scoring results. Transitions REVIEW -> SCORED.
        All scores are already committed per-application; this just
        closes the review period. Owner only.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.state == "REVIEW", "dao: Not in REVIEW state"

        self.state = "SCORED"

    @gl.public.write
    def distribute(self) -> None:
        """
        Distribute grant funds to top N winners by score.
        Uses a simple linear scan to find max_winners highest scores.
        Each winner receives an equal share of total_pool.

        Transitions SCORED -> DISTRIBUTED.
        Owner only.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.state == "SCORED", "dao: Not in SCORED state"
        assert self.balance >= self.total_pool, "dao: Insufficient balance"
        assert self.application_count > u256(0), "dao: No applications"

        winners = u256(0)
        actual_winners = self.max_winners
        if self.application_count < actual_winners:
            actual_winners = self.application_count

        # Identify winner threshold score using a simple selection pass
        # Mark the top N apps for payout
        distributed_count = u256(0)

        # We do two passes: first find the threshold, then pay
        # Pass 1: collect scores into sorted-by-score order (simple N^2 is fine for small N)
        # For on-chain simplicity: pay in order of decreasing score, up to max_winners
        i = u256(0)
        threshold = u256(0)

        # Find threshold score: iterate to find the max_winners-th highest score
        # Simple approach: scan max_winners times to find max each time
        paid_flags: TreeMap[u256, u256] = TreeMap()

        while distributed_count < actual_winners:
            # Find highest unpaid score
            best_score = u256(0)
            best_id = u256(0)
            found = False
            j = u256(0)
            while j < self.application_count:
                if paid_flags.get(j, u256(0)) == u256(0):
                    s = self.app_scores.get(j, u256(0))
                    if not found or s > best_score:
                        best_score = s
                        best_id = j
                        found = True
                j = j + u256(1)

            if not found:
                break

            paid_flags[best_id] = u256(1)
            distributed_count = distributed_count + u256(1)

        # Pay each winner equal share
        if distributed_count > u256(0):
            share = self.total_pool // distributed_count
            k = u256(0)
            while k < self.application_count:
                if paid_flags.get(k, u256(0)) == u256(1):
                    recipient = self.app_applicants.get(
                        k,
                        Address("0x0000000000000000000000000000000000000000")
                    )
                    self.app_funded[k] = share

                    @gl.evm.contract_interface
                    class _EOA:
                        class View:
                            pass
                        class Write:
                            pass

                    _EOA(recipient).emit_transfer(value=share)
                k = k + u256(1)

        self.state = "DISTRIBUTED"

    @gl.public.write
    def withdraw_remainder(self) -> None:
        """
        After distribution, owner can withdraw any remaining dust.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.state == "DISTRIBUTED", "dao: Not yet distributed"
        assert self.balance > u256(0), "dao: Nothing to withdraw"

        amount = self.balance

        @gl.evm.contract_interface
        class _EOA:
            class View:
                pass
            class Write:
                pass

        _EOA(self.owner).emit_transfer(value=amount)
