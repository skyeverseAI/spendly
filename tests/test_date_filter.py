# tests/test_date_filter.py
#
# Feature: Date Filter for Profile Page (Spec: 05-date-filter-profile-page.md)
#
# Tests cover:
#   - All-time (unfiltered) behaviour: no query params → all expenses returned
#   - Valid date filter: both params present, from ≤ to → stats scoped to range
#   - Boundary behaviour: expenses on the from/to dates are included
#   - Filter state variables passed to template (is_filtered, date_from, date_to)
#   - Active-filter badge rendered only when is_filtered is True
#   - Fallback to all-time for every invalid-param combination:
#       · non-date strings
#       · only one param present (from only, to only)
#       · from later than to (inverted range)
#       · empty strings
#   - Each of the three stats (total_spend, category_spends, top_3) is
#     independently verified to respect the filter
#   - Authentication guard: unauthenticated request redirects to /login

import pytest
from tests.conftest import insert_user, insert_expense


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login(client, app, user_id):
    """Inject session state directly to simulate a logged-in user."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Test User"


def get_profile(client, query_string=""):
    url = "/profile"
    if query_string:
        url = f"/profile?{query_string}"
    return client.get(url)


# ---------------------------------------------------------------------------
# Fixtures — shared expense dataset
#
# Two users are created so tests can confirm the filter is also user-scoped.
# User A has expenses spread across two calendar months:
#   April 2026: 100.00 (Food), 200.00 (Bills)          → April total = 300.00
#   May   2026: 50.00  (Transport)                       → May total  =  50.00
#   All-time total                                        = 350.00
# User B has one expense in April (proves no cross-user leakage).
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded(app, client):
    """
    Insert a known dataset and return a dict of user ids and expense metadata.
    """
    user_a_id = insert_user(app, name="Alice", email="alice@example.com")
    user_b_id = insert_user(app, name="Bob",   email="bob@example.com")

    # User A — April 2026
    insert_expense(app, user_a_id, 100.00, "Food",      "2026-04-10", "Groceries")
    insert_expense(app, user_a_id, 200.00, "Bills",     "2026-04-20", "Electricity")
    # User A — May 2026
    insert_expense(app, user_a_id,  50.00, "Transport", "2026-05-01", "Bus pass")

    # User B — April 2026 (must not appear in User A's stats)
    insert_expense(app, user_b_id, 999.00, "Shopping",  "2026-04-15", "Laptop")

    return {"user_a_id": user_a_id, "user_b_id": user_b_id}


# ===========================================================================
# Group 1 — Authentication guard
# ===========================================================================

class TestProfileAuthGuard:

    def test_unauthenticated_request_redirects_to_login(self, client):
        response = get_profile(client)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_request_with_filter_params_redirects_to_login(
        self, client
    ):
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# Group 2 — Unfiltered (all-time) behaviour
# ===========================================================================

class TestProfileUnfiltered:

    def test_no_params_returns_200(self, client, seeded, app):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert response.status_code == 200

    def test_no_params_total_spend_includes_all_user_expenses(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        # 100 + 200 + 50 = 350; amount formatted with two decimal places
        assert b"350" in response.data

    def test_no_params_is_filtered_badge_absent(self, client, seeded, app):
        """
        When no valid filter is active, the active-filter badge must not be
        rendered.  The spec requires is_filtered=False for unfiltered views.
        We verify the badge container is absent by checking the template
        renders without the badge markup.
        """
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        # The badge is only rendered when is_filtered is True.
        # We check that the date-range indicator phrases are absent.
        assert b"filter-badge" not in response.data
        assert b"is_filtered" not in response.data  # raw variable name leaked → bug

    def test_no_params_does_not_leak_other_users_expenses(
        self, client, seeded, app
    ):
        """User A's all-time total must not include User B's 999.00 expense."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"999" not in response.data

    def test_empty_database_returns_zero_total_spend(self, client, app):
        """A user with no expenses should see a total of 0."""
        user_id = insert_user(app, name="Empty", email="empty@example.com")
        login(client, app, user_id)
        response = get_profile(client)
        assert response.status_code == 200
        assert b"0" in response.data


# ===========================================================================
# Group 3 — Valid date filter: total_spend
# ===========================================================================

class TestDateFilterTotalSpend:

    def test_valid_filter_april_only_returns_april_total(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert response.status_code == 200
        # April total = 100 + 200 = 300
        assert b"300" in response.data

    def test_valid_filter_may_only_returns_may_total(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-05-01&to=2026-05-31")
        assert response.status_code == 200
        # May total = 50
        assert b"50" in response.data

    def test_valid_filter_excludes_expenses_outside_range(
        self, client, seeded, app
    ):
        """April filter must not include the May 50.00 expense."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        # All-time total 350 should not appear; only 300 should
        assert b"350" not in response.data

    def test_valid_filter_empty_range_returns_zero(self, client, seeded, app):
        """A valid date range with no matching expenses yields total 0."""
        login(client, app, seeded["user_a_id"])
        # March 2026 — no expenses exist in this range
        response = get_profile(client, "from=2026-03-01&to=2026-03-31")
        assert response.status_code == 200
        assert b"0" in response.data

    def test_valid_filter_does_not_leak_other_users_expenses(
        self, client, seeded, app
    ):
        """User A filtered to April must not include User B's April 999.00."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"999" not in response.data


# ===========================================================================
# Group 4 — Valid date filter: boundary dates are inclusive
# ===========================================================================

class TestDateFilterBoundaryInclusion:

    def test_expense_on_from_date_is_included(self, client, app):
        """An expense whose date equals the from param must be included."""
        user_id = insert_user(app, email="boundary1@example.com")
        insert_expense(app, user_id, 77.00, "Food", "2026-04-01", "On from-date")
        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"77" in response.data

    def test_expense_on_to_date_is_included(self, client, app):
        """An expense whose date equals the to param must be included."""
        user_id = insert_user(app, email="boundary2@example.com")
        insert_expense(app, user_id, 88.00, "Bills", "2026-04-30", "On to-date")
        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"88" in response.data

    def test_expense_one_day_before_from_date_is_excluded(self, client, app):
        """An expense one day before the from param must not be included."""
        user_id = insert_user(app, email="boundary3@example.com")
        insert_expense(app, user_id, 99.00, "Other", "2026-03-31", "Day before from")
        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        # Total should be 0, not 99
        assert b"99" not in response.data

    def test_expense_one_day_after_to_date_is_excluded(self, client, app):
        """An expense one day after the to param must not be included."""
        user_id = insert_user(app, email="boundary4@example.com")
        insert_expense(app, user_id, 55.00, "Food", "2026-05-01", "Day after to")
        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"55" not in response.data

    def test_single_day_range_from_equals_to(self, client, app):
        """from == to is a valid single-day filter."""
        user_id = insert_user(app, email="singleday@example.com")
        insert_expense(app, user_id, 42.00, "Food", "2026-04-15", "Lunch")
        insert_expense(app, user_id, 10.00, "Food", "2026-04-14", "Coffee")
        login(client, app, user_id)
        # Only the 2026-04-15 expense should appear
        response = get_profile(client, "from=2026-04-15&to=2026-04-15")
        assert b"42" in response.data
        assert b"10" not in response.data


# ===========================================================================
# Group 5 — Valid date filter: category_spends stat
# ===========================================================================

class TestDateFilterCategorySpends:

    def test_valid_filter_category_breakdown_only_contains_in_range_categories(
        self, client, seeded, app
    ):
        """
        User A April: Food (100) + Bills (200).  Transport (May) must not
        appear in the category breakdown when the filter is April only.
        """
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"Food" in response.data
        assert b"Bills" in response.data
        # Transport only has a May expense; it must not appear in April view
        assert b"Transport" not in response.data

    def test_unfiltered_category_breakdown_contains_all_categories(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"Food" in response.data
        assert b"Bills" in response.data
        assert b"Transport" in response.data


# ===========================================================================
# Group 6 — Valid date filter: top_3 stat
# ===========================================================================

class TestDateFilterTop3:

    def test_valid_filter_top3_only_shows_in_range_expenses(
        self, client, app
    ):
        """
        Insert 4 expenses: 3 in April, 1 in May.  The May expense must not
        appear in the top-3 when filtered to April.
        """
        user_id = insert_user(app, email="top3@example.com")
        insert_expense(app, user_id, 300.00, "Bills",     "2026-04-05", "Rent")
        insert_expense(app, user_id, 200.00, "Food",      "2026-04-10", "Dinner")
        insert_expense(app, user_id, 100.00, "Transport", "2026-04-15", "Train")
        insert_expense(app, user_id, 999.00, "Shopping",  "2026-05-01", "Big purchase")

        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")

        # April expenses present
        assert b"Rent" in response.data
        assert b"Dinner" in response.data
        assert b"Train" in response.data
        # May expense absent
        assert b"Big purchase" not in response.data

    def test_valid_filter_top3_respects_limit_of_three(self, client, app):
        """Top-3 must never show more than 3 rows even when many match."""
        user_id = insert_user(app, email="top3limit@example.com")
        descriptions = [
            "Alpha", "Beta", "Gamma", "Delta", "Epsilon"
        ]
        amounts = [500, 400, 300, 200, 100]
        for desc, amt in zip(descriptions, amounts):
            insert_expense(app, user_id, amt, "Food", "2026-04-10", desc)

        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")

        # Top 3 descriptions must appear
        assert b"Alpha" in response.data
        assert b"Beta" in response.data
        assert b"Gamma" in response.data
        # 4th and 5th must not appear
        assert b"Delta" not in response.data
        assert b"Epsilon" not in response.data

    def test_unfiltered_top3_shows_overall_highest_expenses(
        self, client, seeded, app
    ):
        """All-time top-3 must include the highest-amount expense regardless of month."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        # Bills (200) is the highest for user A all-time
        assert b"Electricity" in response.data


# ===========================================================================
# Group 7 — is_filtered template variable and active-filter badge
# ===========================================================================

class TestIsFilteredAndBadge:

    def test_valid_filter_renders_active_filter_badge(self, client, seeded, app):
        """
        When is_filtered is True the template must render the active-filter
        badge.  We detect the badge by checking for the 'filter-badge'
        CSS class which the spec says is scoped under '.filter-*'.
        """
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"filter-badge" in response.data

    def test_no_params_does_not_render_active_filter_badge(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"filter-badge" not in response.data

    def test_invalid_params_do_not_render_active_filter_badge(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=abc&to=xyz")
        assert b"filter-badge" not in response.data

    def test_valid_filter_badge_contains_from_date(self, client, seeded, app):
        """The badge must display the active from date so the user can see the range."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"2026-04-01" in response.data

    def test_valid_filter_badge_contains_to_date(self, client, seeded, app):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=2026-04-30")
        assert b"2026-04-30" in response.data

    def test_inverted_range_does_not_render_active_filter_badge(
        self, client, seeded, app
    ):
        """from > to is treated as absent; no badge should appear."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-30&to=2026-04-01")
        assert b"filter-badge" not in response.data


# ===========================================================================
# Group 8 — Invalid param combinations: silent fallback to all-time
# ===========================================================================

class TestInvalidParamsFallback:

    def _assert_all_time_total(self, response, expected_total_substring):
        """
        Helper: verify the response shows the all-time total, not a filtered
        subset.
        """
        assert response.status_code == 200
        assert expected_total_substring in response.data

    def test_non_date_from_and_to_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=abc&to=xyz")
        # All-time total = 350; badge absent
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_from_only_no_to_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_to_only_no_from_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "to=2026-04-30")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_inverted_range_from_greater_than_to_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-30&to=2026-04-01")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_empty_string_params_fall_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=&to=")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_valid_from_invalid_to_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04-01&to=not-a-date")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_invalid_from_valid_to_falls_back_to_all_time(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=not-a-date&to=2026-04-30")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_non_date_params_do_not_cause_500_error(
        self, client, seeded, app
    ):
        """Invalid params must be silently ignored — no server error."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=DROP TABLE expenses;&to=--")
        assert response.status_code == 200

    def test_partial_date_string_falls_back_to_all_time(
        self, client, seeded, app
    ):
        """Partial date like '2026-04' is not a valid YYYY-MM-DD; must fall back."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client, "from=2026-04&to=2026-04")
        assert b"350" in response.data
        assert b"filter-badge" not in response.data

    def test_equal_from_and_to_is_treated_as_valid_not_inverted(
        self, client, app
    ):
        """
        from == to is a degenerate but valid range (a single day).
        The spec states invalid only when from > to, so equal must be accepted.
        """
        user_id = insert_user(app, email="equalrange@example.com")
        insert_expense(app, user_id, 66.00, "Food", "2026-04-15", "Lunch")
        login(client, app, user_id)
        response = get_profile(client, "from=2026-04-15&to=2026-04-15")
        # is_filtered=True: badge present, expense visible
        assert b"filter-badge" in response.data
        assert b"66" in response.data


# ===========================================================================
# Group 9 — Filter form is present in the rendered page
# ===========================================================================

class TestFilterFormPresence:

    def test_profile_page_contains_date_inputs(self, client, seeded, app):
        """The filter form must render two date inputs named 'from' and 'to'."""
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b'name="from"' in response.data
        assert b'name="to"' in response.data

    def test_profile_page_filter_form_uses_get_method(
        self, client, seeded, app
    ):
        """
        The spec requires the filter form to submit via GET so filtered URLs
        are bookmarkable.
        """
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        # Look for method="get" (case-insensitive via lowercase check on decoded data)
        assert b'method="get"' in response.data.lower()

    def test_profile_page_contains_preset_this_month_button(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"This Month" in response.data

    def test_profile_page_contains_preset_last_30_days_button(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"Last 30 Days" in response.data

    def test_profile_page_contains_preset_all_time_button(
        self, client, seeded, app
    ):
        login(client, app, seeded["user_a_id"])
        response = get_profile(client)
        assert b"All Time" in response.data
