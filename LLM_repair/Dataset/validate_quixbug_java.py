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

    for file in sorted(glob.glob(folder + "/*.java")):
        current_file = "_".join(file.split('/')[-1].split("_")[0:-1])
        if ".java" not in current_file:
            current_file = current_file + ".java"
            try:
                index = int(file.split('/')[-1].split("_")[-1].split(".")[0])
            except:
                current_file = file.split('/')[-1]
                index = 0
        else:
            index = 0
        print(current_file, index)

        if len(repair_dict[current_file]) <= index:
            print("Error: {}".format(file))
            continue

        if repair_dict[current_file][index]["finish_reason"] != "stop":
            continue
        if repair_dict[current_file][index]['diff'] == "":
            continue

        bug = current_file.split(".java")[0]
        exit_code = subprocess.run("cd ../QuixBugs; python java_tester.py --bug {} --file {}/{} --add_pf"
                                   .format(bug.lower(), folder, file.split("/")[-1]), shell=True)
                                   #stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if exit_code.returncode == 0:
            plausible += 1
            repair_dict[current_file][index]['valid'] = True
            print("{} has valid patch: {}".format(bug, file))
        else:
            print("{} has invalid patch: {}".format(bug, file))

        total += 1

    print("{}/{} patches are plausible".format(plausible, total))
    with open(folder + "/" + j_file, "w") as f:
        json.dump(repair_dict, f)
