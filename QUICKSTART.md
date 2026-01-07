# Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Calibre is installed:**
   ```bash
   calibredb --version
   ```

   If not found, add Calibre to your PATH:
   - **macOS:** `export PATH="/Applications/calibre.app/Contents/MacOS:$PATH"`
   - Add this to your `~/.zshrc` or `~/.bash_profile` to make it permanent

## First Run

**Note:** A pre-built award database (2,777 records through 2025) is included, so you can skip scraping!

### 1. Preview Changes (Dry Run)

Using the included database (fast):

```bash
python main.py --skip-scrape --dry-run
```

Or scrape fresh data from Wikipedia (takes a few minutes):

```bash
python main.py --dry-run
```

**What happens:**
- Uses award database (included or freshly scraped)
- Matches your Calibre books against awards
- Shows proposed tags in the console
- Creates reports in `data/` directory

### 2. Review Reports

Check the generated reports:
- `data/proposed_changes_<timestamp>.json` - Machine-readable
- `data/proposed_changes_<timestamp>.txt` - Human-readable

### 3. Apply Tags

Once you're satisfied with the matches:

```bash
python main.py
```

You'll be prompted to confirm before tags are applied.

## Optional: Update Award Database

The repository includes a current database, but you can update it to get the latest winners:

```bash
# Refresh caches and scrape all awards
python build_db.py --scrape-all

# Only re-scrape specific awards (load everything else from cache)
python build_db.py --scrape hugo,nebula
```

This will:
- Re-scrape requested awards and refresh per-award caches
- Load remaining awards from cache
- Normalize titles and author names
- Update `data/canonical_awards.csv`

**When to update:**
- After major award ceremonies (Hugo, Nebula, Booker, etc.)
- Periodically (e.g., monthly) to stay current
- Before contributing changes back to the repository

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_matcher.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Common Workflows

### Weekly Update

Add new awards to existing database:

```bash
python main.py
```

### Fresh Start

Rebuild database from scratch:

```bash
python main.py --rebuild-db
```

### Testing Without Scraping

After first run, test matching without re-scraping:

```bash
python main.py --skip-scrape --dry-run
```

### Database-Only Update

Update award database without tagging library:

```bash
# Update database with new awards
python build_db.py --scrape-all

# Or update only a couple of awards and keep everything else from cache
python build_db.py --scrape hugo,nebula
```

Then tag library later:

```bash
python main.py --skip-scrape
```

## Troubleshooting

### "calibredb not found"

**macOS:**
```bash
export PATH="/Applications/calibre.app/Contents/MacOS:$PATH"
```

**Linux:**
```bash
sudo apt-get install calibre
# or
sudo dnf install calibre
```

**Windows:**
Add Calibre installation directory to PATH environment variable.

### "No matches found"

- Verify your Calibre library has award-winning books
- Check book metadata (titles and authors) are accurate
- Lower matching thresholds in `matcher.py` if needed

### Scraping Errors

Wikipedia structure may have changed. Check logs:
```bash
tail -f logs/calibre_tagger_*.log
```

## Understanding the Output

### Match Summary

```
MATCH SUMMARY
================================================================================
Books matched: 15
Total tags to add: 23
================================================================================
Tags by award:
  Hugo: 8
  Nebula: 6
  Booker: 5
  National Book Award: 4
```

### Proposed Changes

```
[BOOK ID: 42]
  Title:   The Fifth Season
  Author:  N.K. Jemisin
  New tags to add:
    - Award: Hugo [Winner] (confidence: 98.5%)
      Matched with: The Fifth Season by N.K. Jemisin (2016)
```

## Tips

1. **Start with dry-run** to preview changes
2. **Review reports** before applying tags
3. **Automatic backups**: The tool creates a timestamped backup of `metadata.db` before making changes (only a few MB, takes <1 second). You can restore by copying it back.
4. **Run periodically** to catch new awards
5. **Check logs** if something goes wrong

## Next Steps

- Customize tag format in `schema.py`
- Adjust matching thresholds in `matcher.py`
- Add more awards to `schema.py` `AWARDS_CONFIG`
- Review `plan.md` for architecture details
