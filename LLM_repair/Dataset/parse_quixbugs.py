import glob
from difflib import unified_diff
import os


def get_unified_diff(source, mutant):
    output = ""
    for line in unified_diff(source.split('\n'), mutant.split('\n'), lineterm=''):
        output += line + "\n"
    return output


def parse_java(folder):
    ret = {}
    for file in sorted(glob.glob(folder + "QuixBugs/Java/fix/*.java")):
        filename = os.path.basename(file)
        with open(file, "r") as f:
            x = f.read().strip()
        with open(folder + "QuixBugs/Java/buggy/{}".format(filename), "r") as f:
            y = f.read().strip()
        ret[filename] = {'fix': x, 'buggy': y, 'diff': get_unified_diff(y, x)}
        print(filename)
        print(get_unified_diff(y, x))
        diff_lines = get_unified_diff(y, x).splitlines()
        remove, gap, add, single_hunk = False, False, False, True
        line_no = 0
        for line in diff_lines[2:]:
            if "@@" in line:
                rline = line.split(" ")[1][1:]
                line_no = int(rline.split(",")[0].split("-")[0])
            elif line.startswith("-"):
                if not remove:
                    start_line_no = line_no
                if gap:
                    single_hunk = False
                remove = True
                end_line_no = line_no
            elif line.startswith("+"):
                if not remove and not add:
                    start_line_no = line_no
                if not add:
                    end_line_no = line_no
                add = True
                if gap:
                    single_hunk = False
            else:
                if remove:
                    gap = True

            if not single_hunk:
                break
            line_no += 1

        if not single_hunk:
            print("Not single hunk bug")
        else:
            print("Single hunk bug")
            ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:start_line_no - 2])
            ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[end_line_no - 2:])

    assert (len(ret) == 40)  # should only be 40 buggy/fix pairs
    return ret


def parse_java_single_line(folder):
    ret = {}
    count = 0
    for file in sorted(glob.glob(folder + "QuixBugs/Java/fix/*.java")):
        filename = os.path.basename(file)
        with open(file, "r") as f:
            x = f.read().strip()
        with open(folder + "QuixBugs/Java/buggy/{}".format(filename), "r") as f:
            y = f.read().strip()
        ret[filename] = {'fix': x, 'buggy': y, 'diff': get_unified_diff(y, x)}
        # print(filename)
        # print(get_unified_diff(y, x))
        diff_lines = get_unified_diff(y, x).splitlines()
        remove, gap, add, single_hunk = False, False, False, True
        line_no = 0
        for line in diff_lines[2:]:
            if "@@" in line:
                rline = line.split(" ")[1][1:]
                line_no = int(rline.split(",")[0].split("-")[0])
            elif line.startswith("-"):
                if not remove:
                    start_line_no = line_no
                if gap:
                    single_hunk = False
                remove = True
                end_line_no = line_no
            elif line.startswith("+"):
                if not remove and not add:
                    start_line_no = line_no
                if not add:
                    end_line_no = line_no
                add = True
                if gap:
                    single_hunk = False
            else:
                if remove:
                    gap = True

            if not single_hunk:
                break
            line_no += 1

        if not single_hunk:
            # print("Not single hunk bug")
            print(filename)
            pass
        else:
            # print("Single hunk bug")
            if end_line_no - start_line_no == 1 or end_line_no == start_line_no:
                ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:start_line_no - 2])
                ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[end_line_no - 2:])
                count += 1
            else:
                # print("Not single line bug")
                print(filename)

    assert (len(ret) == 40)  # should only be 40 buggy/fix pairs
    print(count)
    return ret

def parse_python(folder):
    ret = {}
    for file in glob.glob(folder + "QuixBugs/Python/fix/*.py"):
        filename = os.path.basename(file)
        if "_test" in file or "node.py" in file:
            continue
        with open(file, "r") as f:
            x = f.read().strip()
        with open(folder + "QuixBugs/Python/buggy/{}".format(filename), "r") as f:
            y = f.read().strip()
        ret[filename] = {'fix': x, 'buggy': y, 'diff': get_unified_diff(x, y)}
        print(filename)
        print(get_unified_diff(y, x))
        diff_lines = get_unified_diff(y, x).splitlines()
        line_no = -1
        for line in diff_lines:
            if "@@" in line:
                rline = line.split(" ")[1][1:]
                line_no = int(rline.split(",")[0].split("-")[0])
            elif line_no == -1:
                continue
            if line.startswith("-"):
                ret[filename]['line_no'] = line_no - 2
                ret[filename]['line_content'] = line[1:]
                ret[filename]['type'] = 'modify'
                ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:ret[filename]['line_no']])
                ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[ret[filename]['line_no'] + 1:])
                break
            elif line.startswith("+"):
                ret[filename]['line_no'] = line_no - 2
                ret[filename]['line_content'] = line[1:]
                ret[filename]['type'] = 'add'
                ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:ret[filename]['line_no']])
                ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[ret[filename]['line_no']:])
                break
            line_no += 1

        print(y.splitlines()[ret[filename]['line_no']])

    assert (len(ret) == 40)  # should only be 40 buggy/fix pairs
    return ret