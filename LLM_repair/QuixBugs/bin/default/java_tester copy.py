import argparse
import copy
import json
import sys
import types
import shutil
import signal
import subprocess
import os
import time

from io import StringIO

correct_dir = "../QuixBugs/correct_java_programs"

sys.dont_write_bytecode = True
graph_based = ["breadth_first_search",
               "depth_first_search",
               "detect_cycle",
               "minimum_spanning_tree",
               "reverse_linked_list",
               "shortest_path_length",
               "shortest_path_lengths",
               "shortest_paths",
               "topological_ordering"
               ]

# Used for capturing stdout
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout

def java_try_test(algo):
    try:
        if "correct_java_programs." + algo + "_test" in sys.modules:
            del sys.modules["correct_java_programs." + algo + "_test"]
    except:
        return sys.exc_info()
    
def handler(signum, frame):
    raise TimeoutError("Timeout")
    
def py_try(algo, *args):
    try:
        if "correct_python_programs." + algo in sys.modules:
            del sys.modules["correct_python_programs." + algo]  # hack to reload module
        # this is set even before the first import since its possible that side effects are in file
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5)  # give 5 seconds
        module = __import__("correct_python_programs." + algo)
        fx = getattr(module, algo)
        re = getattr(fx, algo)(*args)
        re = prettyprint(re)
        signal.alarm(0)  # cancel alarm
        return re
    except:
        return sys.exc_info()
    
def py_try_test(algo):
    try:
        if "correct_python_programs." + algo + "_test" in sys.modules:
            del sys.modules["correct_python_programs." + algo + "_test"]  # hack to reload module
            del sys.modules["correct_python_programs." + algo]  # need to reload submodules from test as well, classic
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5)  # give 5 seconds
        correct_module = __import__("correct_python_programs." + algo + "_test")
        correct_fx = getattr(correct_module, algo + "_test")
        output = []
        with Capturing(output) as output:  # need to do this because main has no output ... :(
            getattr(correct_fx, "main")()
        signal.alarm(0)  # cancel alarm
        return ["\n".join(output)]
    except:
        return sys.exc_info()
    
def prettyprint(o):
    if isinstance(o, types.GeneratorType):
        return "(generator) " + str(list(o))
    else:
        return str(o)
    
def move_file_and_copy(src, dest, prefix, postfix):
    with open(src, 'r') as f:
        s = f.read()
    shutil.copy(dest, dest + ".bak")
    with open(dest, 'w') as f:
        if prefix is not None and postfix is not None:
            f.write(prefix + s + postfix)
        else:
            f.write(s)

def compile_java(java_file):
    try:
        subprocess.run(["javac", java_file], check=True)
        print(f"Compiled {java_file} successfully")
    except subprocess.CalledProcessError as e:
        print(f"Compilation error in {e.stderr}: {e}")
        return False
    return True

def compile_java_test(java_file):
    try:
        subprocess.run(["javac", java_file], check=True)
        print(f"Compiled {java_file} successfully")
    except subprocess.CalledProcessError as e:
        print(f"Compilation error in {e.stderr}: {e}")
        return False
    return True

def java_try_test(algo, test_in):
    try:
        # タイムアウトのハンドラ設定（5秒に設定）
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5)  # 5秒の制限時間

        # Javaプログラムの実行コマンドを構築
        java_command = [
            "/usr/bin/java", 
            "-cp", 
            ".:../QuixBugs/correct_java_programs",
            "../QuixBugs/JavaDeserialization_1.java",
            algo
        ] + [json.dumps(arg) for arg in copy.deepcopy(test_in)]
        
        # subprocessでJavaプログラムを実行し、出力とエラーをキャプチャ
        p1 = subprocess.Popen(
            java_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True
        )

        # 出力を読み込む
        java_correct, java_error = p1.communicate()

        # タイムアウト解除
        signal.alarm(0)

        # 出力があるか確認してリストに追加、またはエラー出力を処理
        if java_error:
            return f"Error occurred: {java_error.strip()}"
        else:
            return java_correct.strip()  # 成功時の出力
    except Exception as e:
        return f"Timeout: {e}"
    except Exception as e:
        # その他のエラー発生時の情報を取得
        return f"Exception: {sys.exc_info()}"        
        
def main():
    parser = argparse.ArgumentParser(description='Test Java programs')
    parser.add_argument('--bug', type=str, help='bug to evaluate')
    parser.add_argument('--file', type=str, help='proposed fix in a file')
    parser.add_argument('--add_pf', action='store_true', default=False, help='Use this in conjunction with --file to add the prefix and post fix to the file, '
                             'due to only considering functions we need to add additional code to run')
    args = parser.parse_args() 
    
    print(args)
    correct = []
    patch = []
    prefix, postfix = None, None
    if args.add_pf:
        #load json from file
        with open("../QuixBugs/Java/pf.json", 'r') as f:
            data = json.load(f)
            if args.bug in data:
                prefix = data[args.bug]["prefix"]
                postfix = data[args.bug]["postfix"]
    
    if args.bug in graph_based:
        print("Running correct java:")
        
        # Javaファイルのパスを構築
        testcase_path = os.path.join(correct_dir, f"{args.bug.upper()}_TEST.java")
        print(testcase_path)
        if not os.path.exists(testcase_path):
            print(f"{testcase_path} does not exist")
            return
        
        os.chdir("../QuixBugs")
        print(os.getcwd())
                
        # Javaファイルをコンパイル
        if not compile_java_test(testcase_path):
            shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            print("This is not a correct patch")
            sys.exit(1)
            return
        
        # # パスを元に戻す
        # os.chdir(current_path)
        
        try:
            # print(os.getcwd())
            # タイムアウトのハンドラ設定（5秒に設定）
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(5)  # 5秒の制限時間
            p1 = subprocess.Popen(["java", "../QuixBugs/correct_java_programs/"+args.bug.upper()+"_TEST.java"], stdout=subprocess.PIPE, universal_newlines=True)
            
            java_correct = p1.stdout.read()
            # タイムアウト解除
            signal.alarm(0)
            
            # パスを元に戻す
            os.chdir(current_path)
            
            
            correct.append(java_correct)
            print(prettyprint(java_correct))
            
        except Exception as e:
            # パスを元に戻す
            os.chdir(current_path)
            return f"Timeout: {e}"
        except Exception as e:
            # パスを元に戻す
            os.chdir(current_path)
            # その他のエラー発生時の情報を取得
            return f"Exception: {sys.exc_info()}"
        except:
            # パスを元に戻す
            os.chdir(current_path)
            shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            print(prettyprint(sys.exc_info()))
            
            
        test_class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}_TEST.class"
        print(test_class_file)
        if os.path.exists(test_class_file):
            os.remove(test_class_file)
            print(f"Removed {test_class_file}")
        else:
            print(f"{test_class_file} does not exist")    
            
            
        class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
        print(class_file)
        if os.path.exists(class_file):
            os.remove(class_file)
            print(f"Removed {class_file}")
        else:
            print(f"{class_file} does not exist")
        
        print("Running patch java:")
        move_file_and_copy(args.file, "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()), prefix, postfix)
        print("Moved file")
        
        # Javaファイルのパスを構築
        testcase_path = os.path.join(correct_dir, f"{args.bug.upper()}_TEST.java")
        print(testcase_path)
        if not os.path.exists(testcase_path):
            print(f"{testcase_path} does not exist")
            return
        # 現在のパスを取得
        current_path = os.getcwd()
        print(current_path)
        
        # パスを/local/kusama/APR/LLM_repair/QuixBugsに変更
        os.chdir("../QuixBugs")
        print(os.getcwd())
                
        # Javaファイルをコンパイル
        if not compile_java_test(testcase_path):
            shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            print("This is not a correct patch")
            sys.exit(1)
            return
        
        try:
            # パスを/local/kusama/APR/LLM_repair/QuixBugsに変更
            os.chdir("../QuixBugs")
            # タイムアウトのハンドラ設定（5秒に設定）
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(5)  # 5秒の制限時間
            print("flag1")
            p2 = subprocess.Popen(["java", "../QuixBugs/correct_java_programs/"+args.bug.upper()+"_TEST.java"], stdout=subprocess.PIPE, universal_newlines=True)
            print("flag2")
            try:
                java_patch = p2.communicate(timeout=5)
                print("flag3")
                signal.alarm(0)
                patch.append(java_patch)
                print(prettyprint(java_patch)) 
            except subprocess.TimeoutExpired:
                p2.terminate()
                raise TimeoutError("Timeout")
            
            shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            
            test_class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}_TEST.class"
            print(test_class_file)
            if os.path.exists(test_class_file):
                os.remove(test_class_file)
                print(f"Removed {test_class_file}")
            else:
                print(f"{test_class_file} does not exist")    
            
            class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
            print(class_file)
            if os.path.exists(class_file):
                os.remove(class_file)
                print(f"Removed {class_file}")
            else:
                print(f"{class_file} does not exist")
            
            
            # # signal.alarm(0)
            # print("flag3")
            # java_patch = p2.stdout.read()
            # signal.alarm(0)
            # print("flag4")
            # # タイムアウト解除
            # # signal.alarm(0)
            # patch.append(java_patch)
            # print(prettyprint(java_patch))
            
            # shutil.move("/local/kusama/APR/LLM_repair/QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
            #                 "/local/kusama/APR/LLM_repair/QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            # # if java_correct != java_patch:
            # #     print("This is not a correct patch")
            # #     sys.exit(1)
        except TimeoutError:
            print("flag5")
            p2.terminate()
            shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
            test_class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}_TEST.class"
            print(test_class_file)
            if os.path.exists(test_class_file):
                os.remove(test_class_file)
                print(f"Removed {test_class_file}")
            else:
                print(f"{test_class_file} does not exist")    
            
            class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
            print(class_file)
            if os.path.exists(class_file):
                os.remove(class_file)
                print(f"Removed {class_file}")
            else:
                print(f"{class_file} does not exist")
            
            print(prettyprint(sys.exc_info()))
            sys.exit(1)
    
    else:
        working_file = open("../QuixBugs/json_testcases/" + args.bug + ".json", 'r')
    
        for line in working_file:
            py_testcase = json.loads(line)
            print(py_testcase)
            test_in, test_out = py_testcase
            if not isinstance(test_in, list):
                test_in = [test_in]
                
            print("Running correct java:")
            print(os.getcwd())  # 現在の作業ディレクトリを取得
            # Javaファイルのパスを構築
            correct_java_file_path = os.path.join(correct_dir, f"{args.bug.upper()}.java")
            if not os.path.exists(correct_java_file_path):
                print(f"{correct_java_file_path} does not exist")
                return
                
            # Javaファイルをコンパイル
            if not compile_java(correct_java_file_path):
                shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
                print("This is not a correct patch")
                sys.exit(1)
                return
                
            try:
                # タイムアウトのハンドラ設定（5秒に設定）
                signal.signal(signal.SIGALRM, handler)
                # signal.alarm(5)  # 5秒の制限時間
                p1 = subprocess.Popen(["/usr/bin/java", "-cp", ".:../QuixBugs:../QuixBugs/gson-2.8.2.jar", "../QuixBugs/JavaDeserialization.java", args.bug]+ \
                    [json.dumps(arg) for arg in copy.deepcopy(test_in)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,universal_newlines=True)
                
                # 出力を読み込む
                java_correct = p1.communicate(timeout=5)
                
                # java_error = p1.stderr.read()
                # タイムアウト解除
                signal.alarm(0)
                print(prettyprint(java_correct))
                correct.append(prettyprint(java_correct)) 
                
                # # 出力があるか確認してリストに追加、またはエラー出力を処理
                # if java_error:
                #     print(f"Error occurred: {java_error.strip()}")
                #     return
                # else: # 成功時の出力
                #     print(prettyprint(java_correct))
                #     correct.append(prettyprint(java_correct))
                #     return 
                
            except Exception as e:
                return f"Timeout: {e}"
            except Exception as e:
                # その他のエラー発生時の情報を取得
                return f"Exception: {sys.exc_info()}"
                    
                # print(prettyprint(java_correct))
                # correct.append(prettyprint(java_correct))  
            except:
                print(prettyprint(sys.exc_info()))
            
            # java_correct = java_try_test(args.bug.upper(), test_in)
            # print(prettyprint(java_correct))
            # correct.append(prettyprint(java_correct))
                
            class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
            print(class_file)
            if os.path.exists(class_file):
                os.remove(class_file)
                print(f"Removed {class_file}")
            else:
                print(f"{class_file} does not exist")
            
            print("Running patch java:")
            move_file_and_copy(args.file, "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()), prefix, postfix)
            print("Moved file")
            
            patch_java_file_path = "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper())
            if not os.path.exists(patch_java_file_path):
                print(f"{patch_java_file_path} does not exist")
                return    
            
            # Javaファイルをコンパイル
            if not compile_java(patch_java_file_path):
                shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
                print("This is not a correct patch")
                sys.exit(1)
                return
            
            try:
                # タイムアウトのハンドラ設定（5秒に設定）
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5)  # 5秒の制限時間
                p2 = subprocess.Popen(["/usr/bin/java", "-cp", ".:../QuixBugs:../QuixBugs/gson-2.8.2.jar", "../QuixBugs/JavaDeserialization.java", args.bug]+ \
                    [json.dumps(arg) for arg in copy.deepcopy(test_in)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,universal_newlines=True)
                java_patch = p2.communicate(timeout=5)
                # タイムアウト解除
                signal.alarm(0)
                
                print(prettyprint(java_patch))
                patch.append(prettyprint(java_patch))
                
                shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
                
                class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
                print(class_file)
                if os.path.exists(class_file):
                    os.remove(class_file)
                    print(f"Removed {class_file}")
                if java_correct != java_patch:
                    print("This is not a correct patch")
                    sys.exit(1)
            except:
                shutil.move("../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "../QuixBugs/correct_java_programs/{}.java".format(args.bug.upper()))
                
                class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
                print(class_file)
                if os.path.exists(class_file):
                    os.remove(class_file)
                    print(f"Removed {class_file}")
                if java_correct != java_patch:
                    print("This is not a correct patch")
                    sys.exit(1)
                print(prettyprint(sys.exc_info()))
                
            # class_file = f"/Users/kusamakazuki/lab/kusama/APR/LLM_repair/QuixBugs/correct_java_programs/{args.bug.upper()}.class"
            # if os.path.exists(class_file):
            #     os.remove(class_file)
            #     print(f"Removed {class_file}")
            # else:
            #     print(f"{class_file} does not exist")
                
    test_class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}_TEST.class"
    print(test_class_file)
    if os.path.exists(test_class_file):
        os.remove(test_class_file)
        print(f"Removed {test_class_file}")
    else:
        print(f"{test_class_file} does not exist")    
            
            
    class_file = f"../QuixBugs/correct_java_programs/{args.bug.upper()}.class"
    print(class_file)
    if os.path.exists(class_file):
        os.remove(class_file)
        print(f"Removed {class_file}")
    else:
        print(f"{class_file} does not exist")        
                
    if len(patch) != len(correct):
        print("This is not a correct patch")
        sys.exit(1)
    else:
        for i, _ in enumerate(patch):
            if patch[i] != correct[i]:
                print("This is not a correct patch")
                sys.exit(1)
        print("This is a plausible patch")
        sys.exit(0)
        
if __name__ == "__main__":
    main()