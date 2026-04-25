# Specification: human-readable parsing of DUK validator errors

## Context

The web service accepts XML declarations and runs them through DUK (the Romanian ANAF validator).
The validation result is returned as JSON.

Currently in `runner.py` there is a branch that reads the `.err.txt` file directly and places its entire text
into a single `message` field with code `VALIDATION_ERROR`. **`parser.py` is not called at all** in that path —
it is only used in an alternative (currently unused) path via `parse_output`.

Purpose: split the raw `.err.txt` text into individual structured error objects.
Each object's `message` must be understandable without knowledge of DUK's internal format.
Message language — **Romanian**.

---

## Current response format (before changes)

```json
{
  "status": "error",
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "E: validari globale\n eroare atribut: caen: atribut prezent dar vid nepermis\nE: validari globale\n eroare calcul VAL(19)\n eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)"
    }
  ],
  "warnings": []
}
```

---

## Target response format (after changes)

```json
{
  "status": "error",
  "errors": [
    {
      "code": "ATTR_EMPTY",
      "section": "validari globale",
      "field": "caen",
      "message": "Atributul 'caen' este prezent dar gol — valoarea este obligatorie"
    },
    {
      "code": "CALC_MISMATCH",
      "section": "validari globale",
      "rule": "R65",
      "field": "R17_1",
      "tax_type": "VAL",
      "rate": 19,
      "actual": 0,
      "expected": 8,
      "message": "Eroare de calcul VAL(19%): câmpul R17_1 = 0, valoarea așteptată este 8 conform regulii R65"
    }
  ],
  "warnings": []
}
```

The `message` field is preserved in each object and must be self-explanatory.

---

## Implementation details

### 1. New function in `parser.py`

Add new code at the end of `parser.py`. Do not create a separate file.

Add a public entry point:

```python
def parse_duk_err_txt(raw_text: str) -> tuple[list[dict], list[dict]]:
    """
    Accepts raw text from a DUK `.err.txt` output.
    Returns `(errors, warnings)` — lists of structured objects.
    """
```

Helper functions must be named with the `_duk_` prefix (e.g. `_duk_split_blocks`, `_duk_parse_attr_empty`, etc.)
to avoid collisions with existing helpers such as `_try_parse_xml`, `_extract_messages_from_xml`, `_normalize_text_output`.

---

### 2. Block-splitting algorithm

The raw text consists of blocks. Each block begins with a line starting with `E:` (error) or `W:` (warning),
followed by the section name. Lines inside a block start with a space.

Step 1. Split the text into blocks: a new block starts at every line that begins with `E:` or `W:` (no leading spaces).

Example input:

```
E: validari globale
 eroare atribut: caen: atribut prezent dar vid nepermis
E: validari globale
 eroare calcul VAL(19)
 eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)
```

Resulting blocks — two blocks:

```
Block 1: severity=E, section="validari globale"
  lines = ["eroare atribut: caen: atribut prezent dar vid nepermis"]

Block 2: severity=E, section="validari globale"
  lines = ["eroare calcul VAL(19)", "eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)"]
```

Step 2. For each block, apply a chain of parsers (see section 3) — the first matching parser wins.

Step 3. If no parser matches, create an `UNKNOWN` object.

Step 4. Blocks with `severity=E` go to `errors`, blocks with `severity=W` go to `warnings`.

---

### 3. Error types and recognition rules

#### 3.1 Empty attribute (`ATTR_EMPTY`)

Pattern (appears in one of the block lines):

```
eroare atribut: <FIELD>: atribut prezent dar vid nepermis
```

Result fields:

| Field | Value |
|---|---|
| `code` | `"ATTR_EMPTY"` |
| `section` | section from the block header |
| `field` | attribute name (e.g. `caen`) |
| `message` | `"Atributul '<FIELD>' este prezent dar gol — valoarea este obligatorie"` |

#### 3.2 Calculation mismatch (`CALC_MISMATCH`)

The block contains **both** lines simultaneously:

- `eroare calcul <TYPE>(<RATE>)` — tax type and rate
- `eroare regula: <RULE>: <FIELD> (<ACTUAL>) = <FIELD> calculat conform regulii (<EXPECTED>)`

Result fields:

| Field | Value |
|---|---|
| `code` | `"CALC_MISMATCH"` |
| `section` | section from the block header |
| `rule` | rule id (e.g. `R65`) |
| `field` | field name (e.g. `R17_1`) |
| `tax_type` | tax type (`VAL` or `TVA`) |
| `rate` | integer rate (e.g. `19`) |
| `actual` | actual value in XML, integer |
| `expected` | expected value by rule, integer |
| `message` | `"Eroare de calcul <TYPE>(<RATE>%): câmpul <FIELD> = <ACTUAL>, valoarea așteptată este <EXPECTED> conform regulii <RULE>"` |

Notes: numeric fields (`rate`, `actual`, `expected`) must be returned as integers when parseable, otherwise `null`.

#### 3.3 Unknown (`UNKNOWN`)

If a block does not match any known type:

| Field | Value |
|---|---|
| `code` | `"UNKNOWN"` |
| `section` | section from block header (if extracted) |
| `message` | all block lines joined with ` / ` |

---

### 4. Changes in `runner.py`

Import `parse_duk_err_txt` from `parser` and replace the current `.err.txt` content handling.

Before:

```python
if content.lower() == "ok":
    return {"status": "ok", "errors": [], "warnings": []}

return {
    "status": "error",
    "errors": [{"code": "VALIDATION_ERROR", "message": content}],
    "warnings": []
}
```

After:

```python
if content.lower() == "ok":
    return {"status": "ok", "errors": [], "warnings": []}

errors, warnings = parse_duk_err_txt(content)
return {
    "status": "error" if errors else "ok",
    "errors": errors,
    "warnings": warnings
}
```

---

### 5. Implementation requirements

- All regular expressions must be case-insensitive (`re.IGNORECASE`).
- Numeric fields (`rate`, `actual`, `expected`) must be returned as `int`; on parse error return `None` (JSON `null`).
- Helper functions in `parser.py` must use the `_duk_` prefix.
- Do not modify `app.py`.
- Do not change the signature of the existing `parse_output` function in `parser.py`.
- Cover `parse_duk_err_txt` with unit tests (`pytest`) in `tests/test_parser.py`:
  - One test per error type (`ATTR_EMPTY`, `CALC_MISMATCH`).
  - Test for `UNKNOWN`.
  - Test for mixed input: several blocks of different types in sequence.
  - Test that a `W:` block is returned in `warnings`, not `errors`.

---

## Example: full input -> expected output

Input (`content` from `.err.txt`):

```
E: validari globale
 eroare atribut: caen: atribut prezent dar vid nepermis
E: validari globale
 eroare calcul VAL(19)
 eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)
E: validari globale
 eroare calcul TVA(19)
 eroare regula: R66: R17_2 (0) = R17_2 calculat conform regulii (2)
E: validari globale
 eroare calcul VAL(31)
 eroare regula: R99: R27_1 (96619) = R27_1 calculat conform regulii (8)
E: validari globale
 eroare calcul TVA(31)
 eroare regula: R100: R27_2 (0) = R27_2 calculat conform regulii (2)
```

Expected output:

```json
{
  "status": "error",
  "errors": [
    {
      "code": "ATTR_EMPTY",
      "section": "validari globale",
      "field": "caen",
      "message": "Atributul 'caen' este prezent dar gol — valoarea este obligatorie"
    },
    {
      "code": "CALC_MISMATCH",
      "section": "validari globale",
      "rule": "R65",
      "field": "R17_1",
      "tax_type": "VAL",
      "rate": 19,
      "actual": 0,
      "expected": 8,
      "message": "Eroare de calcul VAL(19%): câmpul R17_1 = 0, valoarea așteptată este 8 conform regulii R65"
    },
    {
      "code": "CALC_MISMATCH",
      "section": "validari globale",
      "rule": "R66",
      "field": "R17_2",
      "tax_type": "TVA",
      "rate": 19,
      "actual": 0,
      "expected": 2,
      "message": "Eroare de calcul TVA(19%): câmpul R17_2 = 0, valoarea așteptată este 2 conform regulii R66"
    },
    {
      "code": "CALC_MISMATCH",
      "section": "validari globale",
      "rule": "R99",
      "field": "R27_1",
      "tax_type": "VAL",
      "rate": 31,
      "actual": 96619,
      "expected": 8,
      "message": "Eroare de calcul VAL(31%): câmpul R27_1 = 96619, valoarea așteptată este 8 conform regulii R99"
    },
    {
      "code": "CALC_MISMATCH",
      "section": "validari globale",
      "rule": "R100",
      "field": "R27_2",
      "tax_type": "TVA",
      "rate": 31,
      "actual": 0,
      "expected": 2,
      "message": "Eroare de calcul TVA(31%): câmpul R27_2 = 0, valoarea așteptată este 2 conform regulii R100"
    }
  ],
  "warnings": []
}
```

---

## Files touched by this task

| File | Action |
|---|---|
| `parser.py` | Add `parse_duk_err_txt` and `_duk_` helpers at the end of the file |
| `runner.py` | Replace `.err.txt` handling to call `parse_duk_err_txt` and return structured errors |
| `tests/test_parser.py` | Add pytest unit tests for `parse_duk_err_txt` |
| `app.py` | Do not change |
