# Google Merchandise Store: traffic and the purchase funnel

One week of Google Merchandise Store traffic, and where those sessions drop out before a purchase.

**Week of data:** 7–13 December 2020. Obfuscated Google Analytics 4 ecommerce export. Citation and limits: [docs/data_source.md](docs/data_source.md).

## Question

Of the sessions that arrive, where do they drop out before a purchase?

## Data

The store sells Google-branded merchandise. The rows are a public, obfuscated GA4 export for Monday 7 December through Sunday 13 December 2020. The week is pre-Christmas, so the rates describe a busy week.

Two limits of this extract belong next to any rate:

1. The client id was stored as a number in the flattened file, so unique-user counts are weaker than session rates. Purchases divided by sessions do not need a perfect user count.
2. The extract is filtered on event date, not session-start date. A session that started before 7 December and continued into the week can have a partial landing page or channel.

The raw extract and the session table are rebuilt locally and are not in this repository. `scripts/download_extract.py` keeps this week from the public flattened file. `scripts/prepare_sessions.py` writes one row per session to `data/processed/funnel_sessions.csv`. The same columns from BigQuery are in `sql/00_bigquery_extract.sql`.

Each session row carries the device, the channel, and the landing page, plus flags for a product view, an in-order add to cart, and an in-order purchase.

## Funnel

Closed funnel:

1. **Session.** Every session.
2. **Product view.** The session has a `view_item` event.
3. **Add to cart.** A `view_item` happens at or before an `add_to_cart`.
4. **Purchase.** That cart happens at or before a `purchase`.

A purchase that skips an earlier step stays in the open purchase count and out of step 4. That gap is a property of the tracking. Channel is a first-match grouping of session source and medium in `scripts/funnel_rules.py`. It is a simplified grouping, separate from the GA4 Default Channel Group and from a data-driven attribution model.

Counts for this week, from `outputs/worked_example_funnel.csv`:

| Step | Sessions | Share of all sessions | Share of the previous step |
| --- | ---: | ---: | ---: |
| 1. Session | 38,739 | 100% | |
| 2. Product view | 8,224 | 21.23% | 21.23% |
| 3. Add to cart | 2,715 | 7.01% | 33.01% |
| 4. Purchase | 577 | 1.49% | 21.25% |

Most sessions never view a product: 30,515 of 38,739 sessions drop off at that step. Of the sessions that add to cart in order, 21.25% reach a closed purchase.

## How to run

Python 3.10 or newer. From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_extract.py
python scripts/prepare_sessions.py
python scripts/run_sql.py sql/01_worked_example_funnel.sql
python scripts/verify.py
```

`download_extract.py` streams about 1.8 GB and keeps one week. On macOS or Linux, activate the virtual environment with `source .venv/bin/activate`.

Optional second view of the same funnel, in pandas:

```bash
python notebooks/01_funnel_walkthrough.py
```

Optional Jupyter: `pip install notebook`, then open `notebooks/01_funnel_walkthrough.ipynb`.

## Repository

| Path | Role |
| --- | --- |
| `scripts/download_extract.py` | Rebuilds the raw week |
| `scripts/prepare_sessions.py` | Events to one row per session |
| `scripts/funnel_rules.py` | Channel rules and closed-funnel flags |
| `scripts/run_sql.py` | Loads the session file into SQLite and runs a SQL file |
| `scripts/verify.py` | Checks channel rules, session grain, and the worked example |
| `scripts/project_config.py` | Paths, dates, and columns |
| `sql/00_bigquery_extract.sql` | Same columns from BigQuery |
| `sql/00_schema.sql` | Session table |
| `sql/01_worked_example_funnel.sql` | Closed funnel and open purchase count |
| `notebooks/01_funnel_walkthrough.py` | Same funnel in pandas |
| `docs/data_source.md` | Citation and limits |
| `outputs/worked_example_funnel.csv` | Funnel counts for this week |
