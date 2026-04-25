import pytest

from app.parser import parse_duk_err_txt


def test_attr_empty():
    content = """
E: validari globale
 eroare atribut: caen: atribut prezent dar vid nepermis
"""
    errors, warnings = parse_duk_err_txt(content)
    assert warnings == []
    assert len(errors) == 1
    e = errors[0]
    assert e["code"] == "ATTR_EMPTY"
    assert e["section"] == "validari globale"
    assert e["field"] == "caen"
    assert e["message"] == "Atributul 'caen' este prezent dar gol — valoarea este obligatorie"


def test_calc_mismatch():
    content = """
E: validari globale
 eroare calcul VAL(19)
 eroare regula: R65: R17_1 (0) = R17_1 calculat conform regulii (8)
"""
    errors, warnings = parse_duk_err_txt(content)
    assert warnings == []
    assert len(errors) == 1
    e = errors[0]
    assert e["code"] == "CALC_MISMATCH"
    assert e["section"] == "validari globale"
    assert e["rule"] == "R65"
    assert e["field"] == "R17_1"
    assert e["tax_type"] == "VAL"
    assert isinstance(e["rate"], int)
    assert e["rate"] == 19
    assert isinstance(e["actual"], int)
    assert e["actual"] == 0
    assert isinstance(e["expected"], int)
    assert e["expected"] == 8
    assert e["message"] == "Eroare de calcul VAL(19%): câmpul R17_1 = 0, valoarea așteptată este 8 conform regulii R65"


def test_unknown():
    content = """
E: some section
 ceva neașteptat
"""
    errors, warnings = parse_duk_err_txt(content)
    assert len(errors) == 1
    e = errors[0]
    assert e["code"] == "UNKNOWN"
    assert e["section"] == "some section"
    assert e["message"] == "ceva neașteptat"


def test_mixed_blocks():
    content = """
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
"""
    errors, warnings = parse_duk_err_txt(content)
    assert len(errors) == 5
    codes = [e["code"] for e in errors]
    assert codes.count("ATTR_EMPTY") == 1
    assert codes.count("CALC_MISMATCH") == 4


def test_warnings_go_to_warnings():
    content = """
W: validari locale
 eroare atribut: caen: atribut prezent dar vid nepermis
"""
    errors, warnings = parse_duk_err_txt(content)
    assert errors == []
    assert len(warnings) == 1
    w = warnings[0]
    assert w["code"] == "ATTR_EMPTY"
    assert w["section"] == "validari locale"
