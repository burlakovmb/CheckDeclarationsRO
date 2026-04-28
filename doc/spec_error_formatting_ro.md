# Specificație: parsare lizibilă a erorilor validatorului DUK

## Context

Serviciul web primește declarații XML și le rulează prin DUK (validatorul ANAF din România).
Rezultatul validării este returnat ca JSON.

În prezent, în `runner.py` există o ramură care citește fișierul `.err.txt` direct și plasează întregul său text
într-un singur câmp `message` cu codul `VALIDATION_ERROR`. **`parser.py` nu este apelat deloc** în acel flux —
este folosit doar într-un traseu alternativ (în prezent nefolosit) prin `parse_output`.

Scop: despărțirea textului brut din `.err.txt` în obiecte de eroare structurate, individuale.
Câmpul `message` al fiecărui obiect trebuie să fie înțeles fără cunoștințe despre formatul intern al DUK.
Limba mesajelor — **română**.

---

## Formatul răspunsului curent (înainte de modificări)

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

## Formatul țintă al răspunsului (după modificări)

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

Câmpul `message` este păstrat în fiecare obiect și trebuie să fie auto-explicativ.

---

## Detalii de implementare

### 1. Funcție nouă în `parser.py`

Adăugați codul la sfârșitul fișierului `parser.py`. Nu creați un fișier separat.

Punctul de intrare public:

```python
def parse_duk_err_txt(raw_text: str) -> tuple[list[dict], list[dict]]:
    """
    Acceptă textul brut dintr-un fișier `.err.txt` generat de DUK.
    Returnează `(errors, warnings)` — liste de obiecte structurate.
    """
```

Funcțiile ajutătoare trebuie să fie numite cu prefixul `_duk_` (de ex. `_duk_split_blocks`, `_duk_parse_attr_empty`, etc.)
pentru a evita coliziunile cu helper-ele existente precum `_try_parse_xml`, `_extract_messages_from_xml`, `_normalize_text_output`.

---

### 2. Algoritmul de separare în blocuri

Textul brut este compus din blocuri. Fiecare bloc începe cu o linie care pornește cu `E:` (eroare) sau `W:` (avertisment),
urmată de numele secțiunii. Liniile din interiorul unui bloc încep cu un spațiu.

Pasul 1. Împărțiți textul în blocuri: un nou bloc începe la fiecare linie care începe cu `E:` sau `W:` (fără spații inițiale).

Exemplu de intrare:

```
E: validari globale
 eroare atribut: caen: atribut prezent dar vid nepermis
E: validari globale
 eroare calcul VAL(19)
 eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)
```

Blocurile rezultate — două blocuri:

```
Block 1: severity=E, section="validari globale"
  lines = ["eroare atribut: caen: atribut prezent dar vid nepermis"]

Block 2: severity=E, section="validari globale"
  lines = ["eroare calcul VAL(19)", "eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)"]
```

Pasul 2. Pentru fiecare bloc, aplicați o succesiune de parser-e (vezi secțiunea 3) — primul parser care se potrivește câștigă.

Pasul 3. Dacă niciun parser nu se potrivește — creați un obiect `UNKNOWN`.

Pasul 4. Blocurile cu `severity=E` merg în `errors`, blocurile cu `severity=W` merg în `warnings`.

---

### 3. Tipuri de erori și reguli de recunoaștere

#### 3.1 Atribut gol (`ATTR_EMPTY`)

Pattern (apare într-una din liniile blocului):

```
eroare atribut: <FIELD>: atribut prezent dar vid nepermis
```

Câmpurile rezultat:

| Câmp | Valoare |
|---|---|
| `code` | `"ATTR_EMPTY"` |
| `section` | secțiunea din header-ul blocului |
| `field` | numele atributului (ex. `caen`) |
| `message` | `"Atributul '<FIELD>' este prezent dar gol — valoarea este obligatorie"` |

---

#### 3.2 Neconcordanță la calcul (`CALC_MISMATCH`)

Blocul conține **ambele** linii simultan:

- `eroare calcul <TYPE>(<RATE>)` — tipul de taxă și cota
- `eroare regula: <RULE>: <FIELD> (<ACTUAL>) = <FIELD> calculat conform regulii (<EXPECTED>)`

Câmpurile rezultat:

| Câmp | Valoare |
|---|---|
| `code` | `"CALC_MISMATCH"` |
| `section` | secțiunea din header-ul blocului |
| `rule` | id-ul regulii (ex. `R65`) |
| `field` | numele câmpului (ex. `R17_1`) |
| `tax_type` | tipul de taxă (`VAL` sau `TVA`) |
| `rate` | cotă, număr întreg (ex. `19`) |
| `actual` | valoarea reală din XML, număr întreg |
| `expected` | valoarea așteptată conform regulii, număr întreg |
| `message` | `"Eroare de calcul <TYPE>(<RATE>%): câmpul <FIELD> = <ACTUAL>, valoarea așteptată este <EXPECTED> conform regulii <RULE>"` |

Notă: câmpurile numerice (`rate`, `actual`, `expected`) trebuie returnate ca `int` dacă pot fi parse-ate, altfel `null`.

---

#### 3.3 Necunoscut (`UNKNOWN`)

Dacă un bloc nu se potrivește niciunui tip cunoscut.

| Câmp | Valoare |
|---|---|
| `code` | `"UNKNOWN"` |
| `section` | secțiunea din header (dacă a fost extrasă) |
| `message` | toate liniile blocului unite cu ` / ` |

---

### 4. Modificări în `runner.py`

Importați `parse_duk_err_txt` din `parser`.

Înlocuiți manipularea curentă a conținutului `.err.txt`:

Înainte:

```python
if content.lower() == "ok":
    return {"status": "ok", "errors": [], "warnings": []}

return {
    "status": "error",
    "errors": [{"code": "VALIDATION_ERROR", "message": content}],
    "warnings": []
}
```

După:

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

### 5. Cerințe de implementare

- Toate expresiile regulate trebuie să fie case-insensitive (`re.IGNORECASE`).
- Câmpurile numerice (`rate`, `actual`, `expected`) trebuie returnate ca `int`; la eroare de parsare returnați `None` (JSON `null`).
- Funcțiile helper din `parser.py` trebuie să folosească prefixul `_duk_`.
- Nu modificați `app.py`.
- Nu schimbați semnătura funcției existente `parse_output` din `parser.py`.
- Acoperiți `parse_duk_err_txt` cu teste unitare (`pytest`) în `tests/test_parser.py`:
  - Un test pentru fiecare tip de eroare (`ATTR_EMPTY`, `CALC_MISMATCH`).
  - Test pentru `UNKNOWN`.
  - Test pentru intrare mixtă: mai multe blocuri de tipuri diferite în secvență.
  - Test că un bloc `W:` este returnat în `warnings`, nu în `errors`.

---

## Exemplu: intrare completă -> rezultat așteptat

Intrare (`content` din `.err.txt`):

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

Rezultat așteptat:

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

## Fișiere afectate de această sarcină

| Fișier | Acțiune |
|---|---|
| `parser.py` | Adăugați `parse_duk_err_txt` și funcții helper `_duk_*` la sfârșitul fișierului |
| `runner.py` | Înlocuiți tratarea `.err.txt` pentru a apela `parse_duk_err_txt` și a returna erori structurate |
| `tests/test_parser.py` | Adăugați teste unitare (`pytest`) pentru `parse_duk_err_txt` |
| `app.py` | Nu modificați |
