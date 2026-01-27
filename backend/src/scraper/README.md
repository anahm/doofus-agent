# Careers scraper

## Usage

```bash
python -m scraper.careers_scraper \
  --url "https://example.com/careers" \
  --job-selector ".job" \
  --title-selector ".job-title" \
  --location-selector ".job-location" \
  --link-selector "a" \
  --db-url "careers.duckdb"
```

Set `CAREERS_DB_URL` or `CAREERS_DB_PATH` to point at a DuckDB/MotherDuck database.
Use `--replace` to delete rows from the same `source_url` before inserting.
