# Efficient Scraping with Caching

The `build_db.py` script implements efficient scraping with per-award caching. This means you only re-scrape the awards you need, and load everything else from cache.

## How It Works

1. **Individual Caches**: Each award is saved to its own file in `data/cache/` (e.g., `hugo.csv`, `giller.csv`)
2. **Selective Scraping**: Specify which awards to re-scrape
3. **Auto-Loading**: Awards not being scraped are loaded from cache
4. **No Redundancy**: Stop hitting Wikipedia/Wikidata for data you already have!

## Usage

### List Available Awards

```bash
python3 build_db.py --list-awards
```

This shows all available awards and whether they're cached:
```
Available awards:
  hugo                      ✓ cached
  nebula                    ✓ cached
  giller                    ✗ not cached
  ...
```

### Scrape Specific Awards

```bash
# Scrape only Giller (load everything else from cache)
python3 build_db.py --scrape giller

# Scrape multiple awards
python3 build_db.py --scrape giller,booker,hugo

# Scrape everything (initial cache building)
python3 build_db.py --scrape-all
```

### Load from Cache Only

```bash
# Build database from cached data (no scraping)
python3 build_db.py
```

## Examples

### First Time Setup

```bash
# Cache all awards initially
python3 build_db.py --scrape-all
```

This takes ~10 minutes but only needs to be done once.

### Update Just One Award

```bash
# Re-scrape just Giller, keep everything else from cache
python3 build_db.py --scrape giller
```

This takes ~5 seconds instead of 10 minutes!

### Recover from Rate Limiting

If you got rate-limited on Booker and International Booker:

```bash
# Wait 30 minutes, then:
python3 build_db.py --scrape booker,international_booker
```

This only re-scrapes those two awards and loads the other 9 from cache.

### Rebuild Entire Database from Cache

```bash
# Just rebuild the combined CSV from cached data
python3 build_db.py
```

Useful if you want to change normalization or deduplication logic.

## Available Awards

The following awards can be scraped individually:

**Wikidata-based** (SPARQL queries):
- `hugo` - Hugo Award for Best Novel
- `nebula` - Nebula Award for Best Novel
- `clarke` - Arthur C. Clarke Award
- `booker` - Booker Prize
- `international_booker` - International Booker Prize
- `locus_scifi` - Locus Award for Science Fiction Novel
- `locus_fantasy` - Locus Award for Fantasy Novel
- `locus_horror` - Locus Award for Horror Novel

**Wikipedia-based** (HTML scraping):
- `agatha` - Agatha Award (all novel categories)
- `national_book_award` - National Book Award for Fiction
- `giller` - Giller Prize

## Benefits

1. **Speed**: Selective scraping is 100x faster
2. **Efficiency**: Don't re-download data you already have
3. **Resilience**: Rate limiting only affects one award
4. **Flexibility**: Easy to update just what's changed

## Single Source of Truth

The legacy build script has been removed. Use `python3 build_db.py` (with optional `--scrape` or `--scrape-all`) for all scraping and cache refreshes.

## Cache Management

- **Location**: `data/cache/*.csv`
- **Format**: Same as canonical database (prize, category, year, status, title, author)
- **Clearing**: Delete `data/cache/` to force a full rebuild
- **Per-award**: Delete specific files to re-scrape just those awards
