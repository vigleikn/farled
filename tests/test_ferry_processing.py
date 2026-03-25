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

def test_process_ferry_csv(tmp_path):
    from scripts.process_ferries import process_ferry_csv

    # Create test CSV
    test_csv = tmp_path / "test_ferries.csv"
    test_csv.write_text("Navn,IMO-nummer,MMSI-nummer\nTest Ferry,123,257122880\n")

    ferries = process_ferry_csv(str(test_csv))
    assert len(ferries) == 1
    assert ferries[0]['name'] == 'Test Ferry'
    assert ferries[0]['mmsi'] == '257122880'