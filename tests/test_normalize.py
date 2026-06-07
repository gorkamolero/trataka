from visa_finder.normalize import company_id, normalize_name


def test_normalize_strips_suffixes_and_punctuation():
    assert normalize_name("Synthetic Software, LLC") == "synthetic software"
    assert normalize_name("Synthetic Software L.L.C.") == "synthetic software"
    assert normalize_name("Acme & Co., Inc.") == "acme and"


def test_company_id_stable_and_state_scoped():
    a = company_id(normalize_name("Synthetic Software LLC"), "MO")
    b = company_id(normalize_name("Synthetic Software L.L.C."), "MO")
    c = company_id(normalize_name("Synthetic Software LLC"), "TX")
    assert a == b           # same company collapses
    assert a != c           # different state -> different id
    assert len(a) == 16
