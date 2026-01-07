# Calibre Awards Tagger

Automatically enrich your Calibre eBook library by identifying and tagging books that have won or been shortlisted for major literary awards.

## Overview


This tool uses a deterministic approach to award tagging:
1. It ships with award data up to 2025, but also includes tools 
2. Builds a canonical awards database
3. Uses fuzzy string matching to correlate your Calibre library against this database
4. Applies award tags to matched books

**Supported Awards:**
- **Sci-Fi/Fantasy:** Hugo, Nebula, Locus, Arthur C. Clarke
- **Literary/General:** Booker Prize, International Booker, National Book Award, Scotiabank Giller Prize
- **Mystery:** Agatha Award

## Included Award Database

This repository includes a **pre-built canonical awards database** (`data/canonical_awards.csv`) with:

  - Agatha: 437 records (1988–2024)
  - Arthur C. Clarke: 239 records (1987–2025)
  - Booker: 470 records (1969–2025)
  - Giller: 327 records (1994–2025)
  - Hugo: 363 records (1953–2025)
  - International Booker: 92 records (2016–2025)
  - Locus: 2512 records (1978–2025)
  - National Book Award: 469 records (1950–2024)
  - Nebula: 376 records (1966–2025)

You can use this database immediately without scraping. To refresh it with the latest awards, run `python build_db.py --scrape-all` (per-award caching), or selectively update with `python build_db.py --scrape hugo,nebula`.

## Requirements

- Python 3.10+
- Calibre installed with `calibredb` command available in PATH
- Internet connection (optional - only needed to rebuild the award database; a pre-built database is included)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd calibre-awards-tagger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify Calibre is installed:
```bash
calibredb --version
```

## Safety & Backups

**Automatic Backup:** When applying tags, this tool automatically creates a backup of your Calibre `metadata.db` file with a timestamp (e.g., `metadata.db.backup-20260106_143022`). This backup is only a few MB and takes less than a second.

**How to Restore:** If anything goes wrong:
1. Close Calibre
2. Navigate to your Calibre Library folder
3. Copy `metadata.db.backup-TIMESTAMP` over `metadata.db`

**Alternative Recovery:** Calibre automatically maintains OPF backup files for each book in the book's folder. You can restore the entire database from these backups:
- Open Calibre → Preferences → Library Maintenance → Restore database

**What This Tool Does:** This tool only **adds** tags to books - it never deletes books, removes existing tags, or modifies other metadata. The risk of data loss is minimal, but we backup metadata.db as a precaution.

**Dry-Run Mode:** Always use `--dry-run` first to preview changes before applying them.

## Usage

### Basic Usage

Run in dry-run mode to see proposed changes without applying them:

```bash
python main.py --skip-scrape --dry-run
```

Apply tags to your Calibre library:

```bash
python main.py --skip-scrape
```

### Advanced Options

```bash
python main.py [OPTIONS]

Options:
  --dry-run       Show proposed changes without applying them
  --rebuild-db    Rebuild the awards database from scratch (otherwise updates incrementally)
  --skip-scrape   Use existing database without re-scraping (faster for testing)
```

### Examples

```bash
# First run: Preview changes using included database
python main.py --skip-scrape --dry-run

# Apply tags to library
python main.py --skip-scrape

# Update database with latest awards and re-tag
python main.py --rebuild-db

# Test matching without scraping again
python main.py --skip-scrape --dry-run
```

### Updating the Database (Optional)

A pre-built database is included, so this is **optional**. Use it to get the latest award winners:

```bash
# Refresh caches and scrape all awards
python build_db.py --scrape-all

# Update just a couple awards and load everything else from cache
python build_db.py --scrape hugo,nebula

# Rebuild from cache only (no network calls)
python build_db.py
```

This is useful for:
- **Updating award data** after new winners are announced
- **Running on a schedule** (e.g., monthly cron job to stay current)
- **Contributing** updated database back to the repository

The included database already has all awards through 2025.

## How It Works

### Phase 1: Knowledge Acquisition

1. **Scraping:** Fetches award data from Wikipedia pages
2. **Normalization:** Cleans and standardizes book titles and author names
3. **Database Building:** Creates `data/canonical_awards.csv`

### Phase 2: Library Enrichment

1. **Extraction:** Reads your Calibre library metadata
2. **Matching:** Uses fuzzy string matching with high thresholds:
   - Author matching (95%+ threshold)
   - Title matching (90%+ threshold, only after author match)
3. **Tag Generation:** Creates tags in format: `Award: Hugo [Winner]`
4. **Application:** Appends tags to matched books

## Tag Format

Tags follow this pattern:

- `Award: Hugo [Winner]` - Hugo Award winner
- `Award: Booker [Shortlist]` - Booker Prize shortlist
- `Award: Agatha, Best First Novel [Nominee]` - Agatha Award nominee

## Project Structure

```
calibre-awards-tagger/
├── main.py                 # Main orchestration script
├── build_db.py            # Database building and scraping
├── lib_interface.py       # Calibre library interface
├── matcher.py             # Fuzzy matching engine
├── report.py              # Report generation
├── schema.py              # Data schema definitions
├── author_normalizer.py   # Author name normalization
├── scrapers/              # Web scraping modules
│   ├── __init__.py
│   ├── base_wiki.py       # Base Wikipedia utilities
│   ├── general_fiction.py # General fiction awards
│   ├── scifi.py          # Sci-fi/fantasy awards
│   └── specialized.py     # Specialized awards
├── tests/                 # Test suite
│   ├── test_base_wiki.py
│   ├── test_matcher.py
│   ├── test_author_normalizer.py
│   └── test_integration.py
├── data/                  # Generated data files
│   ├── canonical_awards.csv
│   ├── author_aliases.json
│   └── proposed_changes_*.json
└── logs/                  # Log files
```

## Data Files

- `data/canonical_awards.csv` - Canonical awards database
- `data/author_aliases.json` - Cached author name normalizations
- `data/proposed_changes_*.json` - Reports of proposed tag changes (generated whenever `main.py` finds matches, in both dry-run and apply modes)
- `logs/calibre_tagger_*.log` - Timestamped execution logs

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test files:

```bash
pytest tests/test_matcher.py
pytest tests/test_integration.py
```

## Configuration

Edit `schema.py` to:
- Add or remove awards
- Modify tag format
- Adjust award categories

Edit `matcher.py` to adjust matching thresholds:
```python
AUTHOR_EXACT_THRESHOLD = 95  # Author matching
TITLE_FUZZY_THRESHOLD = 90   # Title matching
```

## Troubleshooting

### calibredb not found

Ensure Calibre is installed and `calibredb` is in your PATH:
- **macOS:** Add `/Applications/calibre.app/Contents/MacOS/` to PATH
- **Linux:** Install via package manager
- **Windows:** Add Calibre installation directory to PATH

### No matches found

- Ensure your Calibre library has books that won awards
- Check that author names and titles are accurate in your library
- Try lowering matching thresholds in `matcher.py`

### Scraping fails

- Check internet connection
- Wikipedia structure may have changed (inspect logs)
- Use `--skip-scrape` to use existing database

## Incremental Updates

The tool supports incremental updates:
- Awards database is cached in `data/canonical_awards.csv`
- Re-running without `--rebuild-db` adds new records to existing database
- Author aliases are cached to avoid redundant normalization

## Contributing

When adding new awards:

1. Add award configuration to `schema.py` in `AWARDS_CONFIG`
2. Create scraper in appropriate module (`scrapers/`)
3. Add tests for the new scraper
4. Update this README

## License

This project is for personal use. Award data is sourced from Wikipedia under Creative Commons licenses.

## Credits

Built following the blueprint in `plan.md`. Uses:
- BeautifulSoup4 for web scraping
- pandas for data processing
- rapidfuzz for fuzzy string matching
- pytest for testing
