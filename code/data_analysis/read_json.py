import json
import numpy as np
from paths import DUMMY_CATALOG, MAIN_CATALOG


def read_json_file(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def main(use_main=False):
    file_path = MAIN_CATALOG if use_main else DUMMY_CATALOG
    data = read_json_file(str(file_path))
    if data:
        print(f"Number of entries: {len(data)}")
        print("Sample entry:")
        print(json.dumps(data[0], indent=2))

        # Make arrays of the data
        system_name = [entry["System Name"] for entry in data]
        m1 = np.array([entry["M1"] for entry in data])

        print(system_name)
        print(m1)
        # if numerical arrays, show first-column of triplets
        try:
            print(m1[:, 0])
        except Exception:
            pass


if __name__ == "__main__":
    main()
