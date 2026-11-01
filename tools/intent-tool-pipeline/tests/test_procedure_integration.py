"""Control 1.2 continuation/recovery integration; approvals are synthetic fixtures.

Reuse the established behavioral lifecycle cases under the mandatory procedure
binding fixture. No live user approval or specialist judgment is claimed here.
"""
import test_agent_continuation as continuation
import test_agent_rounds as rounds
from test_procedure_binding import root, full_lifecycle  # noqa: F401


def test_bound_synthetic_allowance_replay_and_second_exhaustion(root, full_lifecycle):
    continuation.test_command_approval_replay_resume_and_second_exhaustion_preserve_lifetime_history(root)


def test_bound_missing_user_authority_is_atomic(root, full_lifecycle):
    continuation.test_public_threshold_resolution_missing_or_wrong_user_authority_is_atomic(root)


def test_bound_multiple_items_contract_revisit_and_resume_share_round(root, full_lifecycle):
    rounds.test_multiple_requests_resume_contract_revisit_and_fresh_result_are_one_round(root)


def test_bound_fourth_pass_and_fifth_stop(root, full_lifecycle):
    rounds.test_fourth_pass_is_allowed_and_fifth_modification_is_atomic_stop(root)
