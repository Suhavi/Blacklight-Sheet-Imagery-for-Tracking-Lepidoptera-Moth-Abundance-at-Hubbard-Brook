# Fetching the dataset

Dataset DOI (EDI / PASTA):
https://doi.org/10.6073/pasta/7ac5818bb45bb42c2d935ce7e3756c00

## Option 1 — Manual download (recommended for quick inspection)

Open the DOI link above and click **Download Full Data Package**.

![Download Full Data Package button](../assets/setup/fulldatapackage.png)

## Option 2 — Programmatic download (reproducible)

The DOI resolves to a PASTA data package. You can download the full package as a ZIP via the PASTA API:

```bash
python scripts/download_edi_zip.py --doi 10.6073/pasta/7ac5818bb45bb42c2d935ce7e3756c00 --out data/edi_package.zip
