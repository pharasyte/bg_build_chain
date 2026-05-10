import os
import shutil


def recursive_copy(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy(src, dest)


def mirror_source(source_path, copy_source_to=None, base_path=None, verbose=False):
    if not copy_source_to:
        return None

    destination = copy_source_to
    if base_path:
        relative_path = os.path.relpath(source_path, base_path)
        if verbose:
            print(f"Using directory structure at {copy_source_to} (Base Path: {base_path}, Relative Path: {relative_path})")
        destination = os.path.join(copy_source_to, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)

    if verbose:
        print(f"Copying {source_path} to {destination}")
    shutil.copy(source_path, destination)
    return destination


def copy_extras(extras):
    for extra in extras:
        extra_src = extra.get("src")
        extra_dest = extra.get("dest")
        remove_dest = extra.get("remove_dest", False)
        if extra_src and extra_dest:
            print(f"Copying extra from {extra_src} to {extra_dest}")
            if remove_dest and os.path.exists(extra_dest):
                print(f"Removing existing destination {extra_dest}")
                if os.path.isdir(extra_dest):
                    shutil.rmtree(extra_dest)
                else:
                    os.remove(extra_dest)

            recursive_copy(extra_src, extra_dest)


def copy_assets(assets, assets_dir):
    for asset_path in assets:
        if os.path.exists(asset_path):
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir, exist_ok=True)
            print(f"Copying {asset_path} to {assets_dir}")
            shutil.copy(asset_path, assets_dir)
        else:
            print(f"Asset {asset_path} does not exist. Skipping.")
