# Architecture

## Overview

`micp-predictor` is a local CustomTkinter application for exploratory prediction of MICP treatment outcomes. It trains several scikit-learn regressors for UCS and CCC, compares validation strategies, and attaches diagnostics to predictions.

## Processing flow

```text
Research spreadsheet
  -> schema validation and numeric normalization
  -> cleaning preview and dataset profile
  -> original + engineered features
  -> algorithm comparison
  -> random and paper-grouped validation
  -> selected model bundle
  -> prediction, interval, range, and nearest-sample diagnostics
```

## Modules

- `app.py`: desktop UI, long-running task orchestration, plots, and exports.
- `micp_model.py`: schema, feature engineering, training, validation, model selection, prediction, and reports.
- `tools/`: optional tutorial-document generation utilities.
- `docs/DATA_SCHEMA.md`: public input-field contract without bundling research data.

## Model boundary

Raw literature data, trained model binaries, validation outputs, and temporary analysis scripts are local artifacts and are excluded from Git. The public repository provides code and schema documentation only.

## Scientific limitations

Random folds can overstate generalization when rows from the same paper appear in training and validation. Paper-grouped validation is therefore the preferred scientific signal. Predictions are research aids, not engineering design guarantees.
