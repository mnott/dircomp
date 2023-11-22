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
import shutil
from datetime import datetime # used to convert file time stamps
from pathlib import Path

#
# More Beautiful Tracebacks and Pretty Printing
#
import pydoc
from io import StringIO
from rich import print;
from rich import traceback;
from rich import pretty;
from rich.progress import Progress
import rich.table # used to print a table
from rich.console import Console
pretty.install()
traceback.install()

#
# A global variable to get the count of the total number of files
# We hold it global because of the timeit.timeit() function
#
total_files = 0
differences = 0


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
    diff:  bool = typer.Option(False, "--diff", "-d", help="Whether to show a diff command"),
):
    # call the compare_directories function to compare the two directories based on their size
    compare_directories(files[0], files[1], "size", diff)


#
# ctime command
#
@app.command()
def ctime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
    diff:  bool = typer.Option(False, "--diff", "-d", help="Whether to show a diff command"),
):
    # call the compare_directories function to compare the two directories based on their creation time
    compare_directories(files[0], files[1], "ctime", diff)


#
# mtime command
#
@app.command()
def mtime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
    diff:  bool = typer.Option(False, "--diff", "-d", help="Whether to show a diff command"),
):
    # call the compare_directories function to compare the two directories based on their modification time
    compare_directories(files[0], files[1], "mtime", diff)


#
# atime command
#
@app.command()
def atime (
    files: Optional[List[str]] = typer.Argument(None, help="The files to process"),
    diff:  bool = typer.Option(False, "--diff", "-d", help="Whether to show a diff command"),
):
    # call the compare_directories function to compare the two directories based on their last access time
    compare_directories(files[0], files[1], "atime", diff)

#
# Sync
#
@app.command()
def sync (
    source: str      = typer.Argument(..., help="Source Directory"),
    target: str      = typer.Argument(..., help="Target Directory"),
    dry_run: bool    = typer.Option  (True,  "-d", "--dry_run",   help="Dry Run"),
    overwrite: bool  = typer.Option  (False, "-o", "--overwrite", help="Overwrite Target Files"),
    delete: bool     = typer.Option  (False, "-D", "--delete",    help="Delete Source Files"),
) -> None:
    if dry_run:
        typer.echo("Dry run enabled.")
    merge_directories(source, target, overwrite, delete, dry_run)
    if not dry_run:
        typer.echo(f"Merge completed: '{source}' into '{target}' (overwrite: {overwrite}, delete source: {delete}).")



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
# Count the number of files in a directory tree.
#
def count_files(directory):
    count = 0
    for entry in os.scandir(directory):
        if entry.is_file():
            count += 1
        elif entry.is_dir():
            if not os.path.islink(entry.path):
                count += count_files(entry.path)
    return count

#
# Compare two directories
#
# Not using a recursive function to parse the directories because we want to
# display a progress bar while the directories are being parsed.
#
def parse_directory(path, files, attribute):
    global total_files
    expected_files = count_files(path)

    with Progress() as progress:
        task = progress.add_task(f"Parsing {path}", total=expected_files)
        seen_files = 0
        stack = [path]
        while stack:
            current_path = stack.pop()
            for entry in os.scandir(current_path):
                if entry.is_file():
                    total_files += 1
                    seen_files += 1
                    progress.update(task, advance=1)
                    file_path = os.path.join(entry.path)
                    file_sub_path = remove_prefix(file_path, path)
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
                        stack.append(entry.path)


def compare_directories(path1, path2, what="size", diff=False):
    global total_files, differences

    print (f"Comparing {path1} and {path2} based on {what}")

    files1 = {} # dictionary to hold the files in the first directory
    files2 = {} # dictionary to hold the files in the second directory
    time1  =  0 # variable to hold the time taken to parse the first directory
    time2  =  0 # variable to hold the time taken to parse the second directory
    count1 =  0 # variable to hold the number of files in the first directory
    count2 =  0 # variable to hold the number of files in the second directory

    time1  = timeit.timeit(lambda: parse_directory(path1, files1, what), number=1)
    count1 = total_files

    time2  = timeit.timeit(lambda: parse_directory(path2, files2, what), number=1)
    count2 = total_files - count1

    # create a table to hold the comparison results
    table = rich.table.Table()
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

    if diff:
        table.add_column("Compare", justify="left")

    # Loop through files in Location 1
    for file_path, attribute1 in files1.items():
        if file_path in files2:
            attribute2 = files2[file_path]
            if attribute1 != attribute2:
                differences += 1
                # Add a row to the table for each different file
                if diff:
                    table.add_row(f"{path1}{file_path}", f"{path2}{file_path}", f"{attribute1}", f"{attribute2}", f"diff \"{path1}{file_path}\" \"{path2}{file_path}\"")
                else:
                    table.add_row(f"{path1}{file_path}", f"{path2}{file_path}", f"{attribute1}", f"{attribute2}")
        else:
            differences += 1
            table.add_row(f"{path1}{file_path}", "MISSING", f"{attribute1}", "")

    # Loop through files in Location 2 and check if they're missing in Location 1
    for file_path in files2:
        if file_path not in files1:
            differences += 1
            table.add_row("MISSING", f"{path2}{file_path}", "", files2[file_path])

    # Add header to the table
    if differences == 1:
        table.title = f"[red]{differences}[/red] [green]Different File:[/green]"
    else:
        table.title = f"[red]{differences}[/red] [green]Different Files:[/green]"

    # Get the number of rows in the terminal
    rows, columns = os.popen('stty size', 'r').read().split()

    # Display results
    if differences > 0:
        if differences > int(rows)-5:
            console = Console(file=StringIO())
            console.print(table)
            pydoc.pager(console.file.getvalue())
            console.file.close()
        else:
            rich.print(table)

    # Display statistics
    table_stats = rich.table.Table(show_header=False, show_edge=False, padding=0)
    table_stats.add_column("Label", justify="left")
    table_stats.add_column("Execution Time", justify="right")
    table_stats.add_column("Number of Files", justify="right")
    table_stats.add_row(f"Location 1: {path1}", "{:.6f} seconds".format(time1), "{} files".format(count1))
    table_stats.add_row(f"Location 2: {path2}", "{:.6f} seconds".format(time2), "{} files".format(count2))
    table_stats.add_row(f"Total: ",       "{:.6f} seconds".format(time1+time2), "{} files".format(count2+count1))
    rich.print(table_stats)



# 
# Merge function
#
def merge_directories(source, target, overwrite, delete, dry_run):
    source_path = Path(source)
    target_path = Path(target)

    # Check if source is a directory
    if not source_path.is_dir():
        raise ValueError(f"Source must be a directory: {source}")

    # Check if target is a directory, if not, create it
    if target_path.exists() and not target_path.is_dir():
        raise ValueError(f"Target exists and is not a directory: {target}")
    elif not target_path.exists():
        if dry_run:
            typer.echo(f"Dry run - would create target directory: {target_path}")
        else:
            target_path.mkdir(parents=True)

    total_files = sum(1 for _ in source_path.rglob('*') if _.is_file())

    with Progress() as progress:
        task = progress.add_task("Merging files...", total=total_files)

        for item in source_path.rglob('*'):
            relative_path = item.relative_to(source_path)
            target_item = target_path / relative_path

            if item.is_dir():
                # Handle directory
                if not target_item.exists():
                    action_msg = f"create directory: {target_item}"
                    if dry_run:
                        with progress:
                            typer.echo(f"Dry run - would {action_msg}")
                    else:
                        target_item.mkdir(parents=True, exist_ok=True)
            else:
                # Handle file
                if not target_item.exists() or overwrite:
                    action = "overwrite" if target_item.exists() else "move"
                    action_msg = f"{action}: {item} to {target_item}"
                    if dry_run:
                        with progress:
                            print(f"Dry run - would {action_msg}")
                    else:
                        shutil.move(str(item), str(target_item))
                elif dry_run:
                    with progress:
                        print(f"Dry run - would skip (already exists): {item} to {target_item}")

                # Update progress for files only
                progress.update(task, advance=1)
                

    if delete:
        # Handle delete of empty subdirectories within the source
        for sub_dir in sorted(source_path.rglob('*'), key=lambda x: -str(x.relative_to(source_path)).count(os.sep)):
            if sub_dir.is_dir() and not any(sub_dir.iterdir()):
                if dry_run:
                    with progress:
                        print(f"Dry run - would delete empty directory: {sub_dir}")
                else:
                    sub_dir.rmdir()



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
       size(["a", "d"], False)
    else:
        try:
            app()
        except SystemExit as e:
            if e.code != 0:
                raise
