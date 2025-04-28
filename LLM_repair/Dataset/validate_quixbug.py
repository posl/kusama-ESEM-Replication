# -----------------------------------------------------------------------------
# This project is based on:
# 
# 1. QuixBugs dataset
#    - Original Author: James Koppel
#    - License: MIT License
#    - URL: https://github.com/jkoppel/QuixBugs?tab=MIT-1-ov-file
# 
# 2. Replication package of "Automated Program Repair in the Era of Large Pre-Trained Language Models"
#    - Original Author: Xia Chunqiu, Wei Yuxiang, Zhang Lingming
#    - License: Creative Commons Attribution 4.0 International (CC BY 4.0)
#    - URL: https://zenodo.org/records/7622931
# 
# ----------------------------------------------------------------------------- 
# This code has undergone minor modifications for the purposes of this experiment.
# -----------------------------------------------------------------------------
# Copyright 2017-2019 James Koppel (for QuixBugs dataset)
# 
# Licensed under the MIT License. See LICENSE file for full details.
# -----------------------------------------------------------------------------
import subprocess
import json
import glob

def validate_all_patches(folder, j_file):
    with open(folder + "/" + j_file, "r") as f:
        repair_dict = json.load(f)

    plausible = 0
    total = 0
    bug_counts = {}
    bug_success = {}

    for file in sorted(glob.glob(folder + "/*.py")):
        file_name = file.split('/')[-1]
        bug_name, index_str = file_name.rsplit('.', 1)[0].rsplit('_', 1)
        
        try:
            index = int(index_str)
        except ValueError:
            bug_name = file_name.rsplit('.', 1)[0]
            index = 0

        current_file = f"{bug_name}.py"

        if bug_name not in bug_counts:
            bug_counts[bug_name] = 0
            bug_success[bug_name] = 0

        print(current_file, index)
        if len(repair_dict[current_file]) <= index:
            print("Error: {}".format(file))
            continue

        print(repair_dict[current_file][index]['diff'])
        if repair_dict[current_file][index]['diff'] == "":
            continue

        exit_code = subprocess.run(f"cd ../QuixBugs; python python_tester.py --bug {bug_name} --file {folder}/{file.split('/')[-1]} --add_pf",
                                   shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if exit_code.returncode == 0:
            plausible += 1
            bug_success[bug_name] += 1
            repair_dict[current_file][index]['valid'] = True
            print(f"{bug_name} has valid patch: {file}")
        else:
            print(f"{bug_name} has invalid patch: {file}")

        bug_counts[bug_name] += 1
        total += 1

    print(f"{plausible}/{total} patches are plausible")

    valid_bug_count = sum(1 for bug in bug_counts if bug_success[bug] > 0)
    print(f"{valid_bug_count}/{len(bug_counts)} bugs have at least one valid patch")

    with open(folder + "/" + j_file, "w") as f:
        json.dump(repair_dict, f)