import os
import xml.etree.ElementTree as ET


def _try_parse_xml(tmpdir: str):
    """
    Ищет XML-результаты, которые обычно создаёт валидатор ANAF
    """
    for file in os.listdir(tmpdir):
        if file.lower().endswith(".xml") and file != "input.xml":
            path = os.path.join(tmpdir, file)
            try:
                tree = ET.parse(path)
                return tree.getroot()
            except Exception:
                continue
    return None


def _extract_messages_from_xml(root):
    errors = []
    warnings = []

    if root is None:
        return errors, warnings

    # ANAF валидаторы обычно используют разные теги — ловим максимально гибко
    for elem in root.iter():
        tag = elem.tag.lower()

        text = (elem.text or "").strip()

        if not text:
            continue

        if "error" in tag or "eroare" in tag:
            errors.append({
                "code": "XML_ERROR",
                "message": text
            })

        elif "warn" in tag or "avert" in tag:
            warnings.append({
                "code": "XML_WARNING",
                "message": text
            })

    return errors, warnings


def _normalize_text_output(stdout: str, stderr: str):
    """
    Делит текст на ошибки и предупреждения
    """
    errors = []
    warnings = []

    combined = (stderr or "") + "\n" + (stdout or "")
    lines = [line.strip() for line in combined.splitlines() if line.strip()]

    for line in lines:
        lower = line.lower()

        if any(word in lower for word in ["error", "eroare", "exception"]):
            errors.append({
                "code": "TEXT_ERROR",
                "message": line
            })
        elif any(word in lower for word in ["warning", "avert"]):
            warnings.append({
                "code": "TEXT_WARNING",
                "message": line
            })

    return errors, warnings


def parse_output(tmpdir, process_result):
    stdout = process_result.stdout.decode(errors="ignore")
    stderr = process_result.stderr.decode(errors="ignore")

    # 1️⃣ Пытаемся достать XML-результат
    root = _try_parse_xml(tmpdir)
    xml_errors, xml_warnings = _extract_messages_from_xml(root)

    # 2️⃣ Если XML дал результат — используем его
    if xml_errors or xml_warnings:
        return {
            "status": "error" if xml_errors else "ok",
            "errors": xml_errors,
            "warnings": xml_warnings,
            "raw": stdout
        }

    # 3️⃣ fallback: парсим текст
    text_errors, text_warnings = _normalize_text_output(stdout, stderr)

    if process_result.returncode == 0 and not text_errors:
        return {
            "status": "ok",
            "errors": [],
            "warnings": text_warnings,
            "raw": stdout
        }

    return {
        "status": "error",
        "errors": text_errors or [{
            "code": "VALIDATION_ERROR",
            "message": stderr or stdout or "Unknown validation error"
        }],
        "warnings": text_warnings,
        "raw": stdout
    }


# DUK (.err.txt) parsing utilities
import re
from typing import List, Tuple, Dict, Optional


def _duk_split_blocks(raw_text: str) -> List[Dict]:
    """
    Split raw .err.txt text into blocks. Each block starts with a line
    beginning with 'E:' or 'W:' (no leading spaces) followed by indented lines.
    Returns list of dicts: {'severity': 'E'|'W', 'section': str|None, 'lines': [str,...]}
    """
    blocks: List[Dict] = []
    if not raw_text:
        return blocks

    for line in raw_text.splitlines():
        if not line:
            continue

        # New block starts with E: or W: at the beginning of the line
        if line.startswith("E:") or line.startswith("W:"):
            sev = line[0]
            section = line[2:].strip()
            blocks.append({"severity": sev, "section": section, "lines": []})
            continue

        # Internal lines belong to the last block (if any)
        if blocks:
            blocks[-1]["lines"].append(line.strip())

    return blocks


def _duk_parse_attr_empty(block: Dict) -> Optional[Dict]:
    # pattern: eroare atribut: <FIELD>: atribut prezent dar vid nepermis
    pat = re.compile(r"eroare atribut:\s*([^:]+):\s*atribut prezent dar vid nepermis", re.IGNORECASE)

    for ln in block.get("lines", []):
        m = pat.search(ln)
        if m:
            field = m.group(1).strip()
            message = f"Atributul '{field}' este prezent dar gol — valoarea este obligatorie"
            return {
                "code": "ATTR_EMPTY",
                "section": block.get("section"),
                "field": field,
                "message": message
            }

    return None


def _duk_parse_calc_mismatch(block: Dict) -> Optional[Dict]:
    # need both lines: eroare calcul <TYPE>(<RATE>)  and eroare regula: <RULE>: <FIELD> (<ACTUAL>) = ... (<EXPECTED>)
    calc_re = re.compile(r"eroare calcul\s*(?P<type>VAL|TVA)\s*\(\s*(?P<rate>\d+)\s*\)", re.IGNORECASE)
    regula_re = re.compile(
        r"eroare regula:\s*(?P<rule>R\d+):\s*(?P<field>[A-Za-z0-9_]+)\s*\(\s*(?P<actual>-?\d+)\s*\)\s*=.*\(\s*(?P<expected>-?\d+)\s*\)",
        re.IGNORECASE
    )

    calc_line = None
    regula_line = None

    for ln in block.get("lines", []):
        if calc_re.search(ln):
            calc_line = ln
        if regula_re.search(ln):
            regula_line = ln

    if not (calc_line and regula_line):
        return None

    m_calc = calc_re.search(calc_line)
    m_reg = regula_re.search(regula_line)

    if not (m_calc and m_reg):
        return None

    tax_type = m_calc.group("type").upper()

    def _to_int(s: str) -> Optional[int]:
        try:
            return int(s)
        except Exception:
            return None

    rate = _to_int(m_calc.group("rate"))
    rule = m_reg.group("rule")
    field = m_reg.group("field")
    actual = _to_int(m_reg.group("actual"))
    expected = _to_int(m_reg.group("expected"))

    message = (
        f"Eroare de calcul {tax_type}({rate}%): câmpul {field} = {actual}, "
        f"valoarea așteptată este {expected} conform regulii {rule}"
    )

    return {
        "code": "CALC_MISMATCH",
        "section": block.get("section"),
        "rule": rule,
        "field": field,
        "tax_type": tax_type,
        "rate": rate,
        "actual": actual,
        "expected": expected,
        "message": message
    }


def _duk_make_unknown(block: Dict) -> Dict:
    lines = block.get("lines") or []
    message = " / ".join(lines)
    return {"code": "UNKNOWN", "section": block.get("section"), "message": message}


def parse_duk_err_txt(raw_text: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Принимает сырой текст из .err.txt (DUK-валидator).
    Возвращает (errors, warnings) — списки структурированных объектов.
    """
    errors: List[Dict] = []
    warnings: List[Dict] = []

    blocks = _duk_split_blocks(raw_text or "")

    for b in blocks:
        parsed = _duk_parse_attr_empty(b) or _duk_parse_calc_mismatch(b) or _duk_make_unknown(b)

        if b.get("severity") == "E":
            errors.append(parsed)
        else:
            warnings.append(parsed)

    return errors, warnings