# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import typing


class DaoVeto(gl.Contract):
    """
    DaoVeto — Constitutional AI veto for on-chain governance actions.

    A DAO stores its "constitution" as a set of rules on-chain.
    Before any governance action is executed, it must pass through
    this contract. GenLayer LLM validators check whether the action
    violates any constitutional rule. If it does -> VETOED (blocked).
    If it passes -> ALLOWED (can proceed).

    This is the primitive that makes DAO governance trustless: no
    single admin can push through a rule-breaking action, because
    the AI constitution check cannot be bypassed or censored.

    Workflow:
      1. Owner sets the constitution (immutable after sealing)
      2. Any registered checker submits an action for review
      3. GenLayer validators fetch the action URL + evaluate against all rules
      4. Result stored on-chain: ALLOWED or VETOED with reason
      5. Downstream contracts can query this contract before executing

    State flow per check:
      PENDING -> ALLOWED / VETOED

    Consensus:
      gl.eq_principle.prompt_comparative — validators must agree on
      VETOED or ALLOWED. The constitution text is fixed on-chain so
      all validators evaluate against the same rules.
    """

    # ── CONSTITUTION ──────────────────────────────────────────────
    constitution: str            # The set of rules — immutable after sealing
    constitution_sealed: u256    # 0 = editable, 1 = sealed forever
    dao_name: str
    owner: Address

    # ── CHECKER REGISTRY ──────────────────────────────────────────
    # Only registered checkers can submit actions for review
    checkers: TreeMap[Address, u256]   # 1 = registered
    checker_count: u256

    # ── CHECK STORAGE ─────────────────────────────────────────────
    check_count: u256
    check_titles: TreeMap[u256, str]
    check_descriptions: TreeMap[u256, str]
    check_action_urls: TreeMap[u256, str]
    check_submitters: TreeMap[u256, Address]
    check_states: TreeMap[u256, str]    # PENDING | ALLOWED | VETOED
    check_verdicts: TreeMap[u256, str]
    check_timestamps: TreeMap[u256, u256]

    # ── STATS ─────────────────────────────────────────────────────
    total_allowed: u256
    total_vetoed: u256

    def __init__(
        self,
        dao_name: str,
        constitution: str,
    ):
        """
        Initialize the constitutional veto contract.

        Args:
            dao_name     (str): Name of the DAO
            constitution (str): The full constitution text (>= 100 chars).
                                Write each rule on a new line starting with a number.
                                Example:
                                "1. The DAO may not spend more than 10% of treasury in one vote.
                                 2. No member may hold more than 30% of voting power.
                                 3. Core protocol parameters require 75% supermajority."
        """
        assert len(dao_name) >= 3, "DAO name too short"
        assert len(constitution) >= 100, \
            "Constitution must be at least 100 characters. " \
            "Write numbered rules, one per line."

        self.dao_name = dao_name
        self.constitution = constitution
        self.constitution_sealed = u256(0)
        self.owner = gl.message.sender_address
        self.checker_count = u256(0)
        self.check_count = u256(0)
        self.total_allowed = u256(0)
        self.total_vetoed = u256(0)

    # ── VIEW METHODS ──────────────────────────────────────────────

    @gl.public.view
    def get_constitution(self) -> str:
        return self.constitution

    @gl.public.view
    def is_sealed(self) -> bool:
        return self.constitution_sealed > u256(0)

    @gl.public.view
    def get_dao_info(self) -> str:
        return (
            '{"dao_name": "' + self.dao_name.replace('"', "'") +
            '", "sealed": ' + ("true" if self.constitution_sealed > u256(0) else "false") +
            ', "checker_count": ' + str(self.checker_count) +
            ', "check_count": ' + str(self.check_count) +
            ', "total_allowed": ' + str(self.total_allowed) +
            ', "total_vetoed": ' + str(self.total_vetoed) + '}'
        )

    @gl.public.view
    def get_check(self, check_id: u256) -> str:
        assert check_id < self.check_count, "dao: Invalid check ID"
        return (
            '{"id": ' + str(check_id) +
            ', "title": "' + self.check_titles.get(check_id, "").replace('"', "'") +
            '", "state": "' + self.check_states.get(check_id, "") +
            '", "submitter": "' + self.check_submitters.get(
                check_id,
                Address("0x0000000000000000000000000000000000000000")
            ).as_hex +
            '", "verdict": "' + self.check_verdicts.get(check_id, "").replace('"', "'") +
            '"}'
        )

    @gl.public.view
    def get_check_state(self, check_id: u256) -> str:
        assert check_id < self.check_count, "dao: Invalid check ID"
        return self.check_states.get(check_id, "")

    @gl.public.view
    def is_allowed(self, check_id: u256) -> bool:
        """Convenience method for downstream contracts to query."""
        assert check_id < self.check_count, "dao: Invalid check ID"
        return self.check_states.get(check_id, "") == "ALLOWED"

    @gl.public.view
    def is_checker(self, addr: str) -> bool:
        return self.checkers.get(Address(addr), u256(0)) > u256(0)

    @gl.public.view
    def get_check_count(self) -> u256:
        return self.check_count

    @gl.public.view
    def get_stats(self) -> str:
        return (
            '{"total_checks": ' + str(self.check_count) +
            ', "total_allowed": ' + str(self.total_allowed) +
            ', "total_vetoed": ' + str(self.total_vetoed) + '}'
        )

    # ── WRITE METHODS ─────────────────────────────────────────────

    @gl.public.write
    def submit_for_review(
        self,
        title: str,
        description: str,
        action_url: str,
    ) -> typing.Any:
        """
        Submit a governance action for constitutional review.
        Triggers AI veto check via GenLayer validators.

        Consensus (prompt_comparative):
          Each GenLayer validator fetches the action URL and reads the
          full constitution stored on-chain. The LLM then determines
          whether the proposed action violates any constitutional rule.
          Validators must agree on the same verdict (ALLOWED or VETOED)
          before the result is committed.

        The constitution is fixed on-chain — no validator can use a
        different ruleset. This is the key security property.

        Args:
            title       (str): Short title of the governance action (>= 5 chars)
            description (str): What the action does (>= 40 chars)
            action_url  (str): URL to full action spec or proposal
        """
        assert self.constitution_sealed > u256(0), \
            "dao: Constitution must be sealed before submitting checks"
        assert len(title) >= 5, "dao: Title must be at least 5 characters"
        assert len(description) >= 40, "dao: Description must be at least 40 characters"
        assert len(action_url) > 0, "dao: Action URL required"

        sender = gl.message.sender_address
        assert self.checkers.get(sender, u256(0)) > u256(0) or sender == self.owner, \
            "dao: Not a registered checker"

        cid = self.check_count
        self.check_count = self.check_count + u256(1)

        self.check_titles[cid] = title
        self.check_descriptions[cid] = description
        self.check_action_urls[cid] = action_url
        self.check_submitters[cid] = sender
        self.check_states[cid] = "PENDING"

        constitution_text = self.constitution

        def nondet() -> str:
            action_content = ""
            try:
                response = gl.nondet.web.get(action_url)
                raw = response.body.decode("utf-8")
                action_content = raw[:2000] if len(raw) > 2000 else raw
            except Exception:
                action_content = "[Could not fetch action URL — judging on description only]"

            task = (
                "You are a constitutional AI for a DAO. Your job is to check whether "
                "a proposed governance action violates the DAO's constitution.\n\n"
                "=== DAO CONSTITUTION ===\n" + constitution_text + "\n\n"
                "=== PROPOSED ACTION ===\n"
                "Title: " + title + "\n"
                "Description: " + description + "\n"
                "Full action spec (fetched from URL):\n" + action_content + "\n\n"
                "=== YOUR TASK ===\n"
                "Does this action violate ANY rule in the constitution?\n"
                "If even ONE rule is violated, the answer is VETOED.\n"
                "If no rules are violated, the answer is ALLOWED.\n"
                "Be strict and literal in your interpretation of the constitution.\n"
                "Respond with ONLY 'ALLOWED' or 'VETOED' as the first word, "
                "followed by which rule was violated (or 'no violations found')."
            )
            return gl.nondet.exec_prompt(task)

        verdict = gl.eq_principle.prompt_comparative(
            nondet,
            "The verdicts must reach the same ALLOWED or VETOED conclusion"
        )

        self.check_verdicts[cid] = verdict

        if verdict.strip().startswith("ALLOWED"):
            self.check_states[cid] = "ALLOWED"
            self.total_allowed = self.total_allowed + u256(1)
        else:
            self.check_states[cid] = "VETOED"
            self.total_vetoed = self.total_vetoed + u256(1)

        return verdict

    # ── CONSTITUTION MANAGEMENT ───────────────────────────────────

    @gl.public.write
    def update_constitution(self, new_constitution: str) -> None:
        """
        Update the constitution text. Only allowed before sealing. Owner only.

        Args:
            new_constitution (str): New full constitution text (>= 100 chars)
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.constitution_sealed == u256(0), \
            "dao: Constitution is sealed and cannot be modified"
        assert len(new_constitution) >= 100, \
            "dao: Constitution must be at least 100 characters"

        self.constitution = new_constitution

    @gl.public.write
    def seal_constitution(self) -> None:
        """
        Permanently seal the constitution. After sealing, it cannot be modified.
        Also enables submission of governance actions for review.
        Owner only — this is an irreversible action.
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        assert self.constitution_sealed == u256(0), "dao: Already sealed"
        assert len(self.constitution) >= 100, "dao: Constitution too short to seal"

        self.constitution_sealed = u256(1)

    # ── CHECKER MANAGEMENT ────────────────────────────────────────

    @gl.public.write
    def register_checker(self, checker_address: str) -> None:
        """
        Allow an address to submit governance actions for review. Owner only.

        Args:
            checker_address (str): Hex address of the checker
        """
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        checker = Address(checker_address)
        assert self.checkers.get(checker, u256(0)) == u256(0), "dao: Already registered"

        self.checkers[checker] = u256(1)
        self.checker_count = self.checker_count + u256(1)

    @gl.public.write
    def remove_checker(self, checker_address: str) -> None:
        """Remove a checker. Owner only."""
        assert gl.message.sender_address == self.owner, "dao: Only owner"
        checker = Address(checker_address)
        assert self.checkers.get(checker, u256(0)) > u256(0), "dao: Not registered"

        self.checkers[checker] = u256(0)
        self.checker_count = self.checker_count - u256(1)
