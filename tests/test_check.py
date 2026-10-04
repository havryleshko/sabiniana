from sabiniana.check import check
from sabiniana.price_table import load_price_table


def test_matching_lines_and_one_small_fee_have_no_findings():
    statement = {
        "total_sales": 10000,
        "total_charges": 180,
        "agreed_rate": "0.015",
        "charged_rate": "0.015",
        "fee_lines": [
            {"name": "Interchange", "amount": "100.10"},
            {"name": "Scheme fee", "amount": "69.90"},
            {"name": "Gateway fee", "amount": "10.00"},
        ],
    }
    result = check(statement)
    assert result["effective_rate"] == 180 / 10000
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
    assert result["findings"] == []


def test_fee_lines_that_do_not_add_up():
    result = check(
        {
            "total_charges": 180,
            "fee_lines": [
                {"name": "Interchange", "amount": 100},
                {"name": "Scheme fee", "amount": 75},
            ],
        }
    )
    assert result["findings"] == [
        {
            "code": "lines_do_not_add_up",
            "summary": "Fee lines sum to 175.00 and the statement total is 180.00.",
            "stated_total": "180.00",
            "line_sum": "175.00",
            "difference": "-5.00",
        }
    ]


def test_a_missing_amount_is_not_treated_as_zero():
    result = check(
        {
            "total_charges": 10,
            "fee_lines": [
                {"name": "Interchange", "amount": 10},
                {"name": "Gateway fee"},
            ],
        }
    )
    assert result["findings"][0] == {
        "code": "lines_cannot_be_summed",
        "summary": "These fee lines have no readable amount: Gateway fee.",
        "lines": ["Gateway fee"],
    }
    assert "lines_do_not_add_up" not in {item["code"] for item in result["findings"]}


def test_one_small_fee_is_not_repeated_or_stacked():
    result = check(
        {
            "fee_lines": [
                {"name": "Terminal rental", "amount": 15},
            ]
        }
    )
    assert result["findings"] == []


def test_the_same_small_fee_twice_is_repeated():
    result = check(
        {
            "fee_lines": [
                {"name": "Gateway fee", "amount": "10.00"},
                {"name": "Payment gateway fee", "amount": "4.50"},
            ]
        }
    )
    assert result["findings"] == [
        {
            "code": "repeated_small_fee",
            "summary": "Gateway fee appears 2 times.",
            "category": "gateway",
            "count": 2,
            "names": ["Gateway fee", "Payment gateway fee"],
            "amounts": ["10.00", "4.50"],
        }
    ]


def test_different_small_fees_on_one_statement_are_stacked():
    result = check(
        {
            "fee_lines": [
                {"name": "Monthly statement fee", "amount": 5},
                {"name": "Terminal hire", "amount": 12},
                {"name": "Administration fee", "amount": 7},
            ]
        }
    )
    assert result["findings"] == [
        {
            "code": "stacked_small_fees",
            "summary": "Small fees are stacked: Statement fee, Admin fee, and Terminal rental.",
            "categories": ["statement", "admin", "terminal_rental"],
        }
    ]


def test_pci_non_compliance_is_an_avoidable_penalty():
    result = check(
        {
            "fee_lines": [
                {"name": "PCI Non-Compliance", "amount": "12.50"},
            ]
        }
    )
    assert result["findings"] == [
        {
            "code": "penalty_fee",
            "summary": (
                "PCI non-compliance fee of 12.50 is charged. "
                "It stops once the provider records the practice as PCI compliant."
            ),
            "kind": "pci_non_compliance",
            "name": "PCI Non-Compliance",
            "amount": "12.50",
            "avoidable": True,
        }
    ]


def test_charged_rate_is_compared_only_when_both_rates_are_present():
    agreed_only = check({"agreed_rate": 0.015, "total_sales": 1000, "total_charges": 15})
    assert agreed_only["findings"] == []

    same = check({"agreed_rate": "0.015", "charged_rate": 0.015})
    assert same["findings"] == []

    different = check({"agreed_rate": "0.015", "charged_rate": "0.019"})
    assert different["findings"] == [
        {
            "code": "charged_rate_differs",
            "summary": "Charged rate 0.019 differs from the agreed rate 0.015.",
            "agreed_rate": "0.015",
            "charged_rate": "0.019",
            "difference": "0.004",
        }
    ]


def test_several_findings_stay_in_a_fixed_order_and_do_not_invent_a_gap():
    statement = {
        "total_sales": 20000,
        "total_charges": 100,
        "agreed_rate": 0.015,
        "charged_rate": 0.019,
        "fee_lines": [
            {"name": "Gateway fee", "amount": 10},
            {"name": "Payment gateway fee", "amount": 5},
            {"name": "Statement fee", "amount": 4},
            {"name": "PCI non-compliance", "amount": "9.50"},
        ],
    }
    result = check(statement)
    assert result == check(statement)
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
    assert [item["code"] for item in result["findings"]] == [
        "lines_do_not_add_up",
        "repeated_small_fee",
        "stacked_small_fees",
        "penalty_fee",
        "charged_rate_differs",
    ]
    assert result["findings"][0]["difference"] == "-71.50"
    assert result["findings"][2]["categories"] == ["statement", "gateway"]


def test_price_table_has_cited_averages_and_no_fair_rate():
    table = load_price_table()
    assert table["fair_all_in_rates"] == []
    observed = table["observed_average_msc"]
    assert observed["published"] == "2021-11-03"
    assert observed["data_period"] == "2015-12 to 2018-12"
    assert [(band["name"], band["rate"]) for band in observed["bands"]] == [
        ("Under £15,000", "0.0183"),
        ("£15,000 to £180,000", "0.0130"),
        ("£180,000 to £380,000", "0.0098"),
        ("£380,000 to £1 million", "0.0090"),
        ("£1 million to £10 million", "0.0082"),
        ("£10 million to £50 million", "0.0070"),
        ("£50 million or more", "0.0040"),
    ]


def test_observed_comparison_uses_the_turnover_band_and_does_not_set_a_fair_gap():
    result = check({"total_sales": 10000, "total_charges": 180})
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
    comparison = result["observed_comparison"]
    assert comparison["band"] == "£15,000 to £180,000"
    assert comparison["observed_rate"] == "0.013"
    assert comparison["annual_card_turnover"] == "120000.00"
    assert comparison["annualised_from_statement"] is True
    assert comparison["yearly_difference"] == "600.00"
    assert comparison["published"] == "2021-11-03"
    assert "not a fair price" in comparison["summary"]


def test_turnover_band_boundary_and_a_rate_below_the_average():
    low = check(
        {
            "total_sales": 1000,
            "total_charges": 18,
            "annual_card_turnover": 14999,
        }
    )
    assert low["observed_comparison"]["band"] == "Under £15,000"
    assert low["observed_comparison"]["observed_rate"] == "0.0183"
    assert low["observed_comparison"]["yearly_difference"] == "-4.50"
    assert low["yearly_gap"] is None

    at_boundary = check(
        {
            "total_sales": 1000,
            "total_charges": 18,
            "annual_card_turnover": 15000,
        }
    )
    assert at_boundary["observed_comparison"]["band"] == "£15,000 to £180,000"
    assert at_boundary["observed_comparison"]["annualised_from_statement"] is False
    assert at_boundary["observed_comparison"]["yearly_difference"] == "75.00"


def test_no_sales_means_no_observed_comparison():
    result = check({"total_charges": 180, "fee_lines": [{"name": "Gateway fee", "amount": 10}]})
    assert result["observed_comparison"] is None


def test_an_empty_price_table_does_not_invent_a_comparison():
    result = check({"total_sales": 10000, "total_charges": 180}, price_table={})
    assert result["observed_comparison"] is None
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
