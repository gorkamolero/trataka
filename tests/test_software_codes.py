from visa_finder.config import load_config


def test_software_classification():
    cfg = load_config()
    sw = cfg.software
    assert sw.is_software("541511", None)        # custom programming -> software
    assert sw.is_software("513210", "15-1254")   # software publisher
    assert not sw.is_software("452210", "41-2031")  # retail -> not software
    # NAICS authoritative: a non-software NAICS overrides a software SOC.
    assert not sw.is_software("452210", "15-1252")
    # No NAICS, software SOC -> software (fallback).
    assert sw.is_software(None, "15-1252")
