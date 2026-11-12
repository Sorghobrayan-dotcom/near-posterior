# near-posterior

Work in progress for NEAR HACKATHON (track `thesis`). Not financial advice.

A NEAR investment thesis that treats the other public NEAR theses as evidence. It harmonises
what each one measures, pools their estimates with a random-effects model weighted by how well
they reproduce, and turns the result into one probability that is updated every day and scored
against its own past predictions.

## Status

| Part | State |
|---|---|
| Raw data snapshot (DefiLlama NEAR Intents volume, fees, revenue; NearBlocks charts) | done, sha256 in `data/raw/manifest.json` |
| Daily series reader, fetch day dropped | done, tested |
| `data/claims.csv`: figures read from other theses | empty |
| Harmonisation, pooling, Monte Carlo, forward tests | not written |

## Try it

```
uv sync
uv run pytest -q
```

See: 4 tests pass, offline, from the committed snapshot.

To refresh the snapshot (network): `uv run python -m near_posterior.fetch`.

## Data

| File | Source |
|---|---|
| `data/raw/intents_volume.json` | https://api.llama.fi/summary/dexs/near-intents?dataType=dailyVolume |
| `data/raw/intents_fees.json` | https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees |
| `data/raw/intents_revenue.json` | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue |
| `data/raw/nearblocks_charts.json` | https://api.nearblocks.io/v1/charts |

## License

MIT, see `LICENSE`. Data belongs to its providers.
