#!/usr/bin/env python3
# encoding: utf-8
r"""

Recursively compare two directory trees.

# Overview

This script recursively compares two directory trees and prints the differences.

# Usage

Call the script with the --help as argument to get the help function:

$ dircomp.py --help

# Example

$ dircomp.py size /home/user1/Downloads /home/user2/Downloads

This will compare both directory tries based on their files' sizes.

"""

import os # used to interact with the file system
import sys # used to debug the script
import timeit # to time options
from datetime import datetime # used to convert file time stamps


#
# More Beautiful Tracebacks and Pretty Printing
#
from rich import print;
from rich import traceback;
from rich import pretty;
import rich.table # used to print a table
pretty.install()
traceback.install()

#
# A global variable to get the count of the total number of files
# We hold it global because of the timeit.timeit() function
#
total_files = 0


#
# Command Line Interface
#
import typer # used to create a Command Line Interface (CLI)
from typing import List, Optional

# Command Line Interface
# The typer library is used to create an app object that is used to define the different commands for the script
app = typer.Typer(
    add_completion = False, # disable shell completion
    rich_markup_mode = "rich", # enable rich markup mode
    no_args_is_help=True, # display help when no arguments are passed
    help="Compare two directory trees", # help text to be displayed when the --help option is passed
    epilog="""
    To get help about the script, call it with the --help option.
    """
)

# The app object is used to define four commands: size, ctime, mtime, and atime
@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)

#
# size command
#
@app.command()
def size (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
    old:   bool = typer.Option(False, "--old", "-o", help="Use the older os.walk() function to parse the directories"),
):
    # call the compare_directories function to compare the two directories based on their size
    compare_directories(files[0], files[1], "size", old)


#
# ctime command
#
@app.command()
def ctime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
):
    # call the compare_directories function to compare the two directories based on their creation time
    compare_directories(files[0], files[1], "ctime")


#
# mtime command
#
@app.command()
def mtime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
):
    # call the compare_directories function to compare the two directories based on their modification time
    compare_directories(files[0], files[1], "mtime")


#
# atime command
#
@app.command()
def atime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
):
    # call the compare_directories function to compare the two directories based on their last access time
    compare_directories(files[0], files[1], "atime")



#
# Command: Doc
#
@app.command()
def doc (
    ctx:        typer.Context,
    title:      str  = typer.Option(None,   help="The title of the document"),
    toc:        bool = typer.Option(False,  help="Whether to create a table of contents"),
) -> None:
    print("doc")
    """
    Re-create the documentation and write it to the output file.
    """
    import importlib
    import importlib.util
    import sys
    import os
    import doc2md

    def import_path(path):
        module_name = os.path.basename(path).replace("-", "_")
        spec = importlib.util.spec_from_loader(
            module_name,
            importlib.machinery.SourceFileLoader(module_name, path),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
        return module

    mod_name = os.path.basename(__file__)
    if mod_name.endswith(".py"):
        mod_name = mod_name.rsplit(".py", 1)[0]
    atitle = title or mod_name.replace("_", "-")
    module = import_path(__file__)
    docstr = module.__doc__
    result = doc2md.doc2md(docstr, atitle, toc=toc, min_level=0)
    print(result)


#
# Main function
#
def parse_directory(path: str, original_path: str, files: dict, attribute: str = "size"):
    global total_files

    for entry in os.scandir(path):
        if entry.is_file():
            total_files += 1
            file_path = os.path.join(entry.path)
            file_sub_path = remove_prefix(file_path, original_path)
            if attribute == "size":
                files[file_sub_path] = get_size(file_path)
            elif attribute == "ctime":
                files[file_sub_path] = convert_time(os.path.getctime(file_path))
            elif attribute == "mtime":
                files[file_sub_path] = convert_time(os.path.getmtime(file_path))
            elif attribute == "atime":
                files[file_sub_path] = convert_time(os.path.getatime(file_path))
        elif entry.is_dir():
            if not os.path.islink(entry.path):
                parse_directory(entry.path, original_path, files, attribute)


#
# Older Main function
#
def parse_directory_old(path, files, what = "size"):
    global total_files
    
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if os.path.isfile(os.path.join(dirpath, filename)):
                total_files += 1
                file_path = os.path.join(dirpath, filename)
                file_sub_path = remove_prefix(file_path, path)
                if what == "size":
                    files[file_sub_path] = get_size(file_path)
                elif what == "ctime":
                    files[file_sub_path] = convert_time(os.path.getctime(file_path))
                elif what == "mtime":
                    files[file_sub_path] = convert_time(os.path.getmtime(file_path))
                elif what == "atime":
                    files[file_sub_path] = convert_time(os.path.getatime(file_path))


# compare_directories function is used to compare the two directories
def compare_directories(path1, path2, what="size", old=False):
    global total_files
    files1 = {} # dictionary to hold the files in the first directory
    files2 = {} # dictionary to hold the files in the second directory
    time1  =  0 # variable to hold the time taken to parse the first directory
    time2  =  0 # variable to hold the time taken to parse the second directory
    count1 =  0 # variable to hold the number of files in the first directory
    count2 =  0 # variable to hold the number of files in the second directory

    if(old): 
        time1 = timeit.timeit(lambda: parse_directory(path1, files1, what), number = 1)
        count1 = total_files

        time2 = timeit.timeit(lambda: parse_directory(path2, files2, what), number = 1)
        count2 = total_files - count1
    else:
        time1 = timeit.timeit(lambda: parse_directory(path1, path1, files1, what), number = 1)
        count1 = total_files

        time2 = timeit.timeit(lambda: parse_directory(path2, path2, files2, what), number = 1)
        count2 = total_files - count1

    # create a table to hold the comparison results
    table = rich.table.Table()
    table.title = "Different Files"
    table.add_column("Location 1", justify="left") # column for the file path in the first directory
    table.add_column("Location 2", justify="left") # column for the file path in the second directory

    headers = {
        "size": "Size",
        "ctime": "Created",
        "mtime": "Modified",
        "atime": "Accessed"
    }

    header = headers.get(what, "")

    table.add_column(f"{header} 1", justify="right") # column for the attribute value in the first directory
    table.add_column(f"{header} 2", justify="right") # column for the attribute value in the second directory
    table.add_column("Compare", justify="left") # column for the comparison of the attribute values

    for file_path, attribute1 in files1.items():
        if file_path in files2:
            attribute2 = files2[file_path]
            if attribute1 != attribute2:
                # add a row to the table for each different file
                table.add_row(f"{path1}{file_path}", f"{path2}{file_path}", f"{attribute1}", f"{attribute2}", f"diff \"{path1}{file_path}\" \"{path2}{file_path}\"")
    rich.print(table)

    # create a table to hold the statistics
    table = rich.table.Table(show_header=False, show_edge=False)
    table.add_column("Label", justify="left")
    table.add_column("Execution Time", justify="right")
    table.add_column("Number of Files", justify="right")
    table.add_row(f"Path: {path1}", "{:.6f} seconds".format(time1), "{} files".format(count1))
    table.add_row(f"Path: {path2}", "{:.6f} seconds".format(time2), "{} files".format(count2))
    table.add_row(f"Total: ",       "{:.6f} seconds".format(time1+time2), "{} files".format(count2+count1))
    rich.print(table)



def remove_prefix(text, prefix):
    """
    Helper function to remove the prefix of a string
    """
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def convert_time(time_stamp):
    """
    Helper function to convert a time stamp to a human-readable format
    """
    return datetime.fromtimestamp(time_stamp).strftime("%Y-%m-%d %H:%M:%S")


def get_size(path):
    """
    Helper function to get the size of a file
    """
    size = os.path.getsize(path)
    if size < 1024:
        return f"{size} bytes"
    elif size < pow(1024,2):
        return f"{round(size/1024, 2)} KB"
    elif size < pow(1024,3):
        return f"{round(size/(pow(1024,2)), 2)} MB"
    elif size < pow(1024,4):
        return f"{round(size/(pow(1024,3)), 2)} GB"


#
# Call app Function
#
if __name__ == "__main__":
    if sys.gettrace() is not None:
        size(["a/b", "d"], False)
    else:
        try:
            app()
        except SystemExit as e:
            if e.code != 0:
                raise
