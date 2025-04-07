import argparse
import sys
import torch
import os
import json
import time

sys.path.append(os.path.dirname(os.path.join(sys.path[0], '../../')))  # Hack
sys.path.append(os.path.dirname(os.path.join(sys.path[0], '../../Dataset/')))

from model import LMs
from Dataset.parse_quixbugs import parse_python, get_unified_diff, parse_java, parse_java_single_line
from Repair.prompt import JAVA_LONG_VARY_PROMPT, VARY_BASE_PROMPT
from Repair.util import pick_smallest_example_fix, set_seed, _run_validation


def repair_loop(args, model, prompt, file_name, folder, bug, t_chances, skip_val=True):
    start = time.time()
    repair_result = []
    p_diff = {}
    print("Repairing bug {} ... ".format(file_name.split(".")[0]))
    print(prompt)
    if not model.check_input(prompt, bug['buggy']):
        return 0, False, False, repair_result

    total_times = 0
    while t_chances > 0:
        total_times += 1
        torch.cuda.empty_cache()
        print("Try :{}".format(total_times))
        well, length, outputs, entropies = model.model_predict(prompt, bug['buggy'], do_sample=True,
                                                               num_samples=t_chances)
        t_chances -= args.batch_size
        if well:
            for index, output in enumerate(outputs):
                diff = get_unified_diff(bug['buggy'], output)
                if diff in p_diff:
                    repair_result[p_diff[diff]]['num'] += 1
                    continue
                p_diff[diff] = len(repair_result)
                print(diff)
                repair_result.append({'output': output,
                                      'diff': diff,
                                      'finish_reason': 'stop',
                                      'entropy': entropies[index],
                                      'valid': _run_validation(file_name.split(".")[0],
                                                               file_name.split(".")[0] + "_" + str(
                                                                   len(repair_result)) + "." + file_name.split(".")[1],
                                                               folder, output, skip_val=skip_val),
                                      'num': 1})

    end = time.time()

    print("{} Unique Patches Generated in {}s".format(len(repair_result), end - start))

    return len(repair_result), False, False, repair_result


def repair(args, model, bugs, folder, used_prompt, chances, skip_val=True, only_same=True):
    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(folder + "/prompt.txt", "w") as f:
        f.write(used_prompt)
    with open(folder + "/args.txt", "w") as f:
        f.write(str(args))

    result = {}
    t_generated = 0
    t_unique = 0
    start_t = time.time()
    for file_name, bug in bugs.items():
        if "Collections" in file_name:
            example_bug, example_fix = pick_smallest_example_fix(bugs, file_name, only_same=False)
        else:
            example_bug, example_fix = pick_smallest_example_fix(bugs, file_name, only_same=only_same)
        prompt = used_prompt.format(example_bug=example_bug, example_fix=example_fix, bug=bug['buggy'])
        n_generated, valid, first_try, result[file_name] = repair_loop(args, model, prompt, file_name, folder, bug,
                                                                       chances, skip_val)
        if n_generated >= 1:
            t_generated += chances
            t_unique += len(result[file_name])

    end_t = time.time()

    with open(folder + "/stats.txt", "w") as f:
        f.write("Total generated: {}\n".format(t_generated))
        f.write("Total unique: {}\n".format(t_unique))
        f.write("Total time: {}\n".format(end_t - start_t))

    with open(folder + "/lm_repair.json", "w") as f:  # write to file
        json.dump(result, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="EleutherAI/gpt-neo-1.3B")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--dataset", type=str, default="quixbugs-python",
                        help="Dataset to use, current support: quixbugs-python, quixbugs-java")
    parser.add_argument("--chances", type=int, default=1)
    parser.add_argument("--skip_val", action="store_true", default=False)
    parser.add_argument("--folder", type=str, default="Results/test")
    parser.add_argument("--weight", type=str, default=None)
    parser.add_argument("--seed", type=int, default=420)
    args = parser.parse_args()
    if args.dataset == "quixbugs-python":
        dataset = parse_python(folder='../../')
        prompt = VARY_BASE_PROMPT
        stop = "# Provide a fix for the buggy function"
        args.language = "python"
    elif args.dataset == "quixbugs-java":
        dataset = parse_java(folder='../../')
        prompt = JAVA_LONG_VARY_PROMPT
        stop = "// Provide a fix for the buggy function"
        args.language = "java"
    else:
        print("Unknown dataset: {}".format(args.dataset))
        return -1

    set_seed(args.seed)
    model = LMs(batch_size=args.batch_size, pretrained=args.model_name, stop=stop, weight=args.weight)
    repair(args, model, dataset, args.folder, prompt, args.chances, args.skip_val, only_same=args.dataset.startswith("defects4j"))

if __name__ == '__main__':
    main()
