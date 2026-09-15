# Input data schema

The application reads the first worksheet (`Sheet1`) of an Excel workbook. Column names are matched exactly, so keep the Chinese names and units shown below.

## Required model inputs

| Column | Meaning | Typical unit |
| --- | --- | --- |
| `OD600` | Bacterial culture optical density | dimensionless |
| `脲酶活性U/ml` | Urease activity | U/ml |
| `中值粒径D50` | Median particle size | mm |
| `试样高度mm` | Specimen height | mm |
| `试样内径mm` | Specimen inner diameter | mm |
| `菌液用量` | Bacterial solution amount | keep one consistent unit |
| `胶结液浓度-氯化钙` | Calcium chloride concentration | mol/L |
| `胶结液浓度-尿素` | Urea concentration | mol/L |
| `胶结液处理次数` | Number of cementation treatments | count |
| `胶结液总用量` | Total cementation solution amount | keep one consistent unit |

## Training targets

| Column | Meaning |
| --- | --- |
| `UCS/kpa` | Unconfined compressive strength in kPa |
| `CCC` | Calcium carbonate content; use one consistent definition and unit |

The second worksheet column is used as the paper/source grouping field during grouped validation. Give every source a stable identifier and do not mix several papers under the same identifier.

## Accepted values

- Numeric cells may contain a single number or a textual range such as `1.0-1.2`; ranges are normalized by the parser.
- Blank values are allowed, but too many missing inputs will reduce the usable sample count.
- Heights and diameters must be positive before specimen volume can be calculated.
- Keep units consistent across every row; the application does not automatically convert mixed units.

## Publication note

Do not open an Issue with a confidential workbook attached. If a bug requires sample data, replace identifiers and values with a minimal synthetic example that reproduces the problem.
