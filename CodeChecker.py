import sys
import clang.cindex
import os
import json
import argparse
import subprocess
import shlex
from collections import defaultdict

def load_compile_database(build_dir):
    try:
        return clang.cindex.CompilationDatabase.fromDirectory(build_dir)
    except Exception as e:
        print(f"Failed to load compile database: {e}")
        return None

def load_compile_flags(db, source_file):
    try:
        cmds = db.getCompileCommands(source_file)
        if cmds:
            return [arg for arg in cmds[0].arguments][1:]  # skip compiler name
    except Exception as e:
        print(f"Failed to get compile commands for {source_file}: {e}")
    return []

def get_all_files_from_compile_commands(build_dir):
    compile_commands_path = os.path.join(build_dir, 'compile_commands.json')
    if not os.path.exists(compile_commands_path):
        print(f"Missing compile_commands.json in {build_dir}")
        return []

    with open(compile_commands_path) as f:
        data = json.load(f)
        return [entry['file'] for entry in data]

def parse_with_compile_commands(source_file, db):
    index = clang.cindex.Index.create()
    args = load_compile_flags(db, source_file)
    print(f"args: {args}")
    # return index.parse(source_file, args=['-std=c++11', '-I./test/inc']) #TODO: change args to use compilation database
    return index.parse(source_file, args=['-I./test/inc', '-DDEBUG', '-Wall', '-g'])

def find_source_files(root_dir, extensions=('.c', '.cpp', '.cc', '.cxx')):
    sources = []
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith(extensions):
                sources.append(os.path.join(dirpath, file))
    return sources

def generate_compile_command(project_root, source_file, include_dirs=[], compiler='clang++', extra_flags=[]):
    command = [compiler]
    command.extend(extra_flags)
    for inc in include_dirs:
        command.append(f"-I{inc}")
    command.append(project_root)
    command.append(source_file)
    return {
        "directory": os.path.dirname(os.path.abspath(source_file)),
        "command": " ".join(command),
        "file": source_file
    }

def extract_compile_commands_from_make(project_root, output_path, include_dirs, compiler, extra_flags, use_make=True, cwd=None):
    make_command = ["make", "--dry-run", "-C", project_root]
    if use_make:
        try:
            proc = subprocess.run(make_command, capture_output=True, text=True, check=True, cwd=cwd)
        except subprocess.CalledProcessError as e:
            print("Error running make:")
            print(e.stderr)
            return []

        compile_commands = []
        for line in proc.stdout.splitlines():
            if line.startswith(('gcc', 'g++', 'clang', 'clang++')):
                args = shlex.split(line)
                src_files = [arg for arg in args if arg.endswith(('.c', '.cpp', '.cc', '.cxx'))]
                if not src_files:
                    continue
                compile_commands.append({
                    "directory": os.path.join(cwd or os.getcwd(), project_root),
                    "command": line,
                    "file": os.path.abspath(os.path.join(cwd or '.', project_root, src_files[0]))
                })
    else:
        source_files = find_source_files(project_root)
        compile_commands = [
            generate_compile_command(project_root, src, include_dirs, compiler, extra_flags)
            for src in source_files
        ]

    with open(output_path, 'w') as f:
        json.dump(compile_commands, f, indent=2)

    print(f"Generated {output_path} with {len(compile_commands)} entries.")

def is_system_header(cursor):
    try:
        header = cursor.location.file
        return header is None or (header.name.startswith("/usr/include") or header.name.startswith("/usr/lib") or "/lib/gcc" in header.name)
    except:
        return False

def build_call_graph(node, current_func=None, call_graph=None, all_functions=None):
    if call_graph is None:
        call_graph = defaultdict(list)
    if all_functions is None:
        all_functions = set()

    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL or clang.cindex.CursorKind.CXX_METHOD:
        if node.kind == clang.cindex.CursorKind.CXX_METHOD:
            current_func = node.semantic_parent.spelling + "::" + node.spelling
        elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            current_func = node.spelling
        else:
            pass #nop
            # print(f"DEBUG: {node.kind} {node.spelling}")

        if current_func:
            all_functions.add(current_func)

    # print(f"\nDEBUG: current {current_func}")
    for child in node.get_children():
        if is_system_header(child):
            continue
        if current_func and child.kind in [
            clang.cindex.CursorKind.CALL_EXPR,
        ]:
            for gc in child.get_children():
                # print(f"DEBUG: {gc.kind} {gc.type.spelling} {gc.spelling}")
                if gc.kind == clang.cindex.CursorKind.MEMBER_REF_EXPR:
                    for cxx in gc.get_children():
                        # print(f"DEBUG: {cxx.type.spelling}::{gc.spelling}")
                        f = cxx.type.spelling + "::" + gc.spelling
                        call_graph[current_func].append(f)
                    break
            else:
                call_graph[current_func].append(child.spelling)

        build_call_graph(child, current_func, call_graph, all_functions)

    return call_graph, all_functions

def find_root_functions(call_graph):
    all_called = set()
    for callees in call_graph.values():
        all_called.update(callees)

    return [f for f in call_graph if f not in all_called]

def print_call_graph(call_graph, start_func, lenght=0):

    if start_func is None:
        return
    lenght += len(start_func) + 2
    if start_func in call_graph:
        for callee in call_graph[start_func]:
            if len(call_graph[start_func]) > 1:
                print("")
                for i in range(lenght):
                    print(" ",end="")
                print("|",end="")
            if callee is None:
                print(f"-> {callee}",end="")
            else:
                print(f"-> {callee}()",end="")
            print_call_graph(call_graph, callee, lenght)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate Call Graph using libclang.")
    parser.add_argument("project_root", help="Path to the project root.")
    parser.add_argument("--generate_compile_commands", action="store_true", help="Generate compile_commands.json.")
    parser.add_argument("--include", nargs='*', default=[], help="Include directories (-I).")
    parser.add_argument("--compiler", default="clang++", help="Compiler to use.")
    parser.add_argument("--flags", nargs='*', default=[], help="Extra compiler flags.")

    args = parser.parse_args()
    compile_commands_path = args.project_root + "/compile_commands.json"
    extract_compile_commands_from_make(args.project_root, compile_commands_path, args.include, args.compiler, args.flags)

    if args.generate_compile_commands:
        sys.exit(1)

    db = load_compile_database(args.project_root)

    if not db:
        sys.exit(1)

    source_files = get_all_files_from_compile_commands(args.project_root)
    global_call_graph = defaultdict(list)
    all_functions = set()

    for cpp_file in source_files:
        print(f"{cpp_file}")
        try:
            tu = parse_with_compile_commands(cpp_file, db)
            call_graph, funcs = build_call_graph(tu.cursor)
            for func in funcs:
                # print(f"{func}: {call_graph[func]}")
                global_call_graph[func] = call_graph[func]
            all_functions.update(funcs)
        except clang.cindex.TranslationUnitLoadError as e:
            print(f"Error parsing {cpp_file}: {e}")
    
    all_funcs = sorted(all_functions)

    if not all_funcs:
        print("No functions found in the file.")
        sys.exit(0)
    
    # print(f"All functions:")
    for func in all_funcs:
        # print(f"{func}: {global_call_graph[func]}")
        if len(global_call_graph[func]) == 0:
            global_call_graph[func].append(None)

    root_funcs = find_root_functions(global_call_graph)

    if not root_funcs:
        print("No root functions found.")
    else:
        print("\nCall graph:",end="")
        for root_func in root_funcs:
            # print(f"\nRoot: {call_graph[root_func]}")
            # if call_graph[root_func][0] is None:
            #     continue
            print(f"\n{root_func}()",end="")
            print_call_graph(global_call_graph, root_func)
    print("")
