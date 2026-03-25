def test_validate_mmsi():
    from scripts.process_ferries import validate_mmsi
    assert validate_mmsi("257122880") == True
    assert validate_mmsi("123") == False
    assert validate_mmsi("") == False

def test_validate_norwegian_waters():
    from scripts.process_ferries import validate_norwegian_waters
    assert validate_norwegian_waters(59.0, 10.0) == True  # Oslo
    assert validate_norwegian_waters(45.0, 10.0) == False  # Too south
    assert validate_norwegian_waters(85.0, 10.0) == False  # Too north