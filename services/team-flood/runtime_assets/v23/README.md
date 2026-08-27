# V23 runtime assets

The cached V23 media bundle is intentionally distributed through GitHub
Releases instead of Git. Run `python scripts/setup_v23.py` after cloning, or
set `V23_ASSET_ROOT` to an installed bundle. The installer verifies every file
against `config/runtime_assets_v23.json`.

The shared Sokrisan source is stored at
`regions/sokrisan/sokrisan_region_digital_twin_base_v23.mp4`. All V23 events whose
address resolves to Chungcheongbuk-do / Boeun-gun / Sokrisan-myeon select this region
asset before any legacy Osong field-profile media. Its 46-second source tail is held
to the 60-second personalized-visual boundary.
