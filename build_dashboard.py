"""
Собирает дашборд «Процентная маржа Сбербанка» из результатов ноутбука.

Вход (папка parsed, их пишет шаг 4 ноутбука):
    metrics.csv      — ставки и средние остатки по кварталам
    rate_volume.csv  — водопад rate-volume
    funding_mix.csv  — структура фондирования (необязательно: без него блок не показывается)
Шаблон:  dashboard_template.html (лежит рядом с этим скриптом)
Выход:   sber_nim_dashboard.html — открывается в любом браузере, интернет не нужен.

Запуск:  python build_dashboard.py                              # пути по умолчанию (ниже)
         python build_dashboard.py data docs/index.html        # папка с CSV и куда сохранить HTML
"""
import json
import sys
from pathlib import Path

import pandas as pd

PARSED   = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Admin\cbr_data\parsed")
OUT      = Path(sys.argv[2]) if len(sys.argv) > 2 else PARSED / "sber_nim_dashboard.html"
TEMPLATE = Path(__file__).with_name("dashboard_template.html")

# Ключевая ставка ЦБ: дата вступления решения в силу → ставка, %.
# Новое решение — просто добавь строку в конец.
KEY_RATE = [
    ("2019-12-16", 6.25), ("2020-02-10", 6.00), ("2020-04-27", 5.50), ("2020-06-22", 4.50), ("2020-07-27", 4.25),
    ("2021-03-22", 4.50), ("2021-04-26", 5.00), ("2021-06-15", 5.50), ("2021-07-26", 6.50), ("2021-09-13", 6.75),
    ("2021-10-25", 7.50), ("2021-12-20", 8.50), ("2022-02-14", 9.50), ("2022-02-28", 20.0), ("2022-04-11", 17.0),
    ("2022-05-04", 14.0), ("2022-05-27", 11.0), ("2022-06-14", 9.50), ("2022-07-25", 8.00), ("2022-09-19", 7.50),
    ("2023-07-24", 8.50), ("2023-08-15", 12.0), ("2023-09-18", 13.0), ("2023-10-30", 15.0), ("2023-12-18", 16.0),
    ("2024-07-29", 18.0), ("2024-09-16", 19.0), ("2024-10-28", 21.0), ("2025-06-09", 20.0), ("2025-07-28", 18.0),
    ("2025-09-15", 17.0), ("2025-10-27", 16.5), ("2025-12-22", 16.0), ("2026-02-16", 15.5), ("2026-03-23", 15.0),
    ("2026-04-27", 14.5), ("2026-06-22", 14.25), ("2026-07-27", 14.0),
]


def quarter_of(report_date):
    """Отчётная дата → квартал, который перед ней закончился: 2026-07-01 → '2026Q2'."""
    return str((pd.Timestamp(report_date) - pd.Timedelta(days=1)).to_period("Q"))


m = pd.read_csv(PARSED / "metrics.csv")
m["q"] = m["quarter_end"].map(quarter_of)
rv = pd.read_csv(PARSED / "rate_volume.csv", index_col=0).iloc[:, 0]

# Средняя ключевая ставка за квартал: ставка на каждый день, потом среднее по дням квартала
quarters = pd.period_range(m["q"].iloc[0], m["q"].iloc[-1], freq="Q")
daily = (pd.Series({pd.Timestamp(d): v for d, v in KEY_RATE})
           .reindex(pd.date_range(KEY_RATE[0][0], quarters[-1].end_time.normalize())).ffill())
key = {str(q): round(daily[q.start_time:q.end_time.normalize()].mean(), 3) for q in quarters}

data = {
    "quarters": [str(q) for q in quarters],
    "key": key,
    "rows": m[["q", "loans_avg", "funds_avg", "assets_avg", "loan_interest", "funds_interest", "nii",
               "loan_yield_%", "funds_cost_%", "spread_%", "nim_%"]].round(3).to_dict("records"),
    "rv": [[name, float(v)] for name, v in rv.items()],
}
# Структура фондирования: остатки на отчётную дату → квартал, на конец которого они даны
mix_path = PARSED / "funding_mix.csv"
if mix_path.exists():
    f = pd.read_csv(mix_path, index_col=0)
    data["funding"] = {
        "cols": list(f.columns),
        "rows": [{"q": quarter_of(d), **{c: round(float(v), 3) for c, v in row.items()}} for d, row in f.iterrows()],
    }

html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print("Готово:", OUT)
