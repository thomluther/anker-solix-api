import zipfile
import json
from typing import Any, Dict, List

def parse_ank_x1_export(file_path: str) -> Dict[str, Any]:
    """
    Parses the Anker Solix X1 system export file and returns a dictionary with the extracted data.

    :param file_path: The path to the Anker Solix X1 system export file.
    :return: A dictionary containing the extracted data.
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Assuming the JSON file is named 'data.json' within the zip file
            with zip_ref.open('data.json') as json_file:
                data = json.load(json_file)
        return data
    except zipfile.BadZipFile:
        raise ValueError("The provided file is not a valid zip file.")
    except FileNotFoundError:
        raise ValueError("The file was not found at the specified path.")
    except json.JSONDecodeError:
        raise ValueError("The file does not contain valid JSON data.")

def test_parse_ank_x1_export():
    """
    Test cases for the parse_ank_x1_export function.
    """
    # Test with a valid export file
    try:
        data = parse_ank_x1_export('test_data/ankxx_2025-02-02_1122.zip')
        assert isinstance(data, dict), "The function should return a dictionary."
        print("Test with valid file passed.")
    except Exception as e:
        print(f"Test with valid file failed: {e}")

    # Test with a non-existent file
    try:
        parse_ank_x1_export('non_existent_file.zip')
    except ValueError as e:
        assert str(e) == "The file was not found at the specified path."
        print("Test with non-existent file passed.")

    # Test with a non-zip file
    try:
        parse_ank_x1_export('test_data/invalid_file.txt')
    except ValueError as e:
        assert str(e) == "The provided file is not a valid zip file."
        print("Test with non-zip file passed.")

    # Test with a zip file that does not contain a valid JSON
    try:
        parse_ank_x1_export('test_data/invalid_zip.zip')
    except ValueError as e:
        assert str(e) == "The file does not contain valid JSON data."
        print("Test with invalid JSON passed.")

# Uncomment the following lines to run the test cases
# test_parse_ank_x1_export()