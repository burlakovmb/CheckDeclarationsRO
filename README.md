# Declarations Checking
# Declarations Checking

[**EN**]
```en
# Declarations Checking (DUK-Integrator)

Name
Check Declarations Service (DUK-Integrator)

Description
This project provides a small validation service and runner that invoke the official DUK-Integrator (ANAF) to validate Romanian fiscal XML declarations and then normalize the validator output into structured JSON responses.

Current state
- Minimal runner and helper scripts in the `app/` folder (Windows and container-friendly).
- `parser.py` contains parsers and specifications for converting raw DUK outputs into structured errors.
- `runner.py` orchestrates invoking DUK, reading `.err.txt` output and (planned) parsing via `parser.parse_duk_err_txt()`.
- `doc/` contains the error-formatting specification (Romanian and English).
- Tests live under `tests/` (pytest).

Quick start (Windows)
1. Install Python 3.10+ and dependencies:
  pip install -r app/requirements.txt
2. Run the local runner (provided helper):
  build and run.bat

Run tests
pytest -q

Notes for developers
- DUK produces messages in Romanian. The parser aims to convert raw `.err.txt` into a list of structured error and warning objects, each containing a `code`, human-friendly `message` (in Romanian), and optional fields such as `field`, `rule`, `tax_type`, `rate`, `actual`, `expected`.
- See `doc/spec_error_formatting.md` (RO) and `doc/spec_error_formatting_en.md` (EN) for the parsing specification.

IMPORTANT!!!
If you would like to use this functionality in your commercial projects then contact me.
Absolutly free for open source projects (non commercial usage). 
```

[**RO**]
```ro
# Verificarea Declarațiilor (DUK-Integrator)

Nume
Serviciul de verificare a declarațiilor (DUK-Integrator)

Descriere
Acest proiect oferă un runner și utilitare care apelează DUK-Integrator (ANAF) pentru a valida declarațiile fiscale în format XML și normalizează ieșirea validatorului în răspunsuri JSON structurate.

Stare curentă
- Runner și scripturi auxiliare în folderul `app/` (compatibil Windows și containere).
- `parser.py` conține parser-ele și specificațiile pentru conversia ieșirii DUK în erori structurate.
- `runner.py` orchestrează rularea DUK, citirea fișierului `.err.txt` și (planificat) parsarea prin `parser.parse_duk_err_txt()`.
- `doc/` conține specificația formatării erorilor (în română și engleză).
- Testele se află în `tests/` (pytest).

Pornire rapidă (Windows)
1. Instalează Python 3.10+ și dependențele:
  pip install -r app/requirements.txt
2. Rulează runner-ul local (script ajutător):
  build and run.bat

Rulare teste
pytest -q

Note pentru dezvoltatori
- DUK returnează mesaje în limba română. Parser-ul convertește textul brut din `.err.txt` într-o listă de obiecte structurate de erori și avertismente, fiecare având `code`, `message` (în română) și câmpuri opționale ca `field`, `rule`, `tax_type`, `rate`, `actual`, `expected`.
- Vezi `doc/spec_error_formatting.md` (RO) și `doc/spec_error_formatting_en.md` (EN) pentru specificația parser-ului.

IMPORTANT!!!
Dacă doriți să utilizați această funcționalitate în proiectele dvs. comerciale, contactați-mă.
Absolut gratuit pentru proiecte open source (utilizare necomercială).
```
Future improvements and team contributions are welcome.
