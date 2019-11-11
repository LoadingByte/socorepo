import os
import shutil


def default_config():
    src_dir = os.path.join(os.path.dirname(__file__), "../socorepo/default_config")
    dst_dir = os.path.abspath("config")

    if os.path.exists(dst_dir):
        print(f"Destination directory '{dst_dir}' already exists. Please delete it and then try again.")
        return

    print(f"Extracting default Socorepo config files to '{dst_dir}'...")
    shutil.copytree(src_dir, "config")
    print("Done!")
