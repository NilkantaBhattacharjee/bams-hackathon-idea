def test_bulk_chart_data_matches_table_totals():
    # The chart source must add up to the same case count as the table.
    import pandas as pd

    from config import CASES_CSV
    from metrics import bottleneck_per_case, load_cases

    df = load_cases(CASES_CSV)
    bn = bottleneck_per_case(df)
    counts = bn.groupby("Stage").size()
    assert int(counts.sum()) == len(bn)
    # Open cases that stopped at Stage 1 have no stage duration, so only cases that reached Stage 2 count.
    reached_stage_2 = df["Stage_2_Timestamp"].notna()
    assert len(bn) == int(reached_stage_2.sum())
    assert isinstance(pd.Series(counts), pd.Series)


def test_app_module_imports():
    # Catches syntax and import errors in app.py that the other tests would not reach.
    import app

    assert callable(app.main)
    assert callable(app.chat_panel)
    assert callable(app.landing)
