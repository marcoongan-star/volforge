# Milestone 14: volatility-sensitivity analysis

This milestone asks a more useful quantitative question than “which agent won?”: does that conclusion survive plausible changes to an uncertain model input?

## Experiment design

The API evaluates earnings jump-volatility assumptions of 4%, 8%, and 12%. Each cell runs 500 trials using the same base seed and the same seed offsets. The market-maker and directional agent therefore face paired terminal markets within a cell, and the cells use common random numbers to reduce irrelevant simulation noise when comparing assumptions.

For each level, VolForge reports the paired mean P&L difference, its large-sample 95% confidence interval, and each agent's 5% expected shortfall. The interval classification is mechanical:

- Above zero: directional advantage in the tested synthetic experiment.
- Below zero: market-maker advantage in the tested synthetic experiment.
- Crossing zero: inconclusive.

## Measured synthetic result

With the published balanced inputs and base seed 14000, the classification changes from market-maker advantage at 4%, to inconclusive at 8%, to directional advantage at 12%. The answer is not robust to the tested volatility assumption. That is more informative—and more honest—than selecting the most favorable single run.

## System design

The Python experiment function owns calculations and validation. FastAPI serializes Decimal results and labels the data synthetic. The public React page displays the measured 500-trial output, while the tested endpoint supports different bounded inputs. No result is described as expected live performance.

## What Marco should understand

Sensitivity analysis exposes model risk. A confidence interval quantifies Monte Carlo sampling uncertainty conditional on a model; changing volatility tests uncertainty about the model itself. A narrow interval does not rescue a conclusion that reverses when a reasonable assumption changes.

## Verification

- All 44 Python tests pass.
- The sensitivity experiment is deterministic and rejects duplicate levels.
- The API preserves synthetic and common-random-number labels.
- Frontend lint, production build, and both server-render checks pass.
