from wholefarm.cap2er_level2 import (
    LEVEL2_INDICATORS,
    IndicatorValue,
    empty_level2_report,
    merge_level2_results,
)


def test_level2_public_indicator_structure_is_preserved() -> None:
    report = empty_level2_report()
    assert len(report) == len(LEVEL2_INDICATORS)
    assert "Nitrogen balance" in report
    assert "GHG emissions" in report
    assert "Treatment Frequency Index" in report
    assert all(item.status == "not_computable" for item in report.values())


def test_level2_computed_indicator_can_be_merged_without_filling_others() -> None:
    report = merge_level2_results(
        {
            "Nitrogen balance": IndicatorValue(
                name="Nitrogen balance",
                category="nitrogen",
                value=20.0,
                unit="kg N/ha UAA",
                status="computed",
            )
        }
    )
    assert report["Nitrogen balance"].status == "computed"
    assert report["Crop diversity"].status == "not_computable"