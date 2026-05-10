import json
import os
from dataclasses import dataclass

from bgs_tools.constellation.config.arguments import build_parser
from bgs_tools.constellation.config.constants import CONFIG_DEFAULTS, DEFAULT_IMPORT, DEFAULT_OUTPUT


@dataclass
class BuildConfig:
    args: object
    values: dict
    verbose: bool
    project_namespace: str | None
    preprocessor_imports: list[str]
    import_dir: list[str]
    output_dir: str
    copy_source_to: str | None
    assets_dir: str | None
    assets: list[str]
    extras: list[dict]
    compiler_path: str
    build_dir: str


def load_config(config_name):
    if not os.path.exists(config_name):
        return None

    with open(config_name, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_config(config_path, config):
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=4)


def merge_config(args, config=None):
    merged_config = {} if config is None else dict(config)
    arg_options = [value for value in args.__dir__() if not value.startswith("_")]

    for arg_name in arg_options:
        if getattr(args, arg_name):
            merged_config[arg_name] = getattr(args, arg_name)

    return merged_config


def verify_or_create_directory(name, directory):
    if not os.path.exists(directory):
        dir_exists = False
        while not dir_exists:
            answer = input(f"Directory {directory} does not exist. (c)reate/(m)odify/(e)xit? ")
            if answer == "e":
                raise SystemExit()
            if answer == "c":
                print(f"Creating directory {directory}")
                os.makedirs(directory)
                dir_exists = True
            elif answer == "m":
                directory = input(f"Enter {name} directory: ")
            else:
                raise ValueError(f"Invalid answer {answer}")

    return directory


def get_project_imports(project_dir, loaded_projects=None):
    if loaded_projects is None:
        loaded_projects = [os.getcwd()]

    print(f"Getting imports for {project_dir}")
    imports = [os.path.join(project_dir, "src", "papyrus")]
    print(f"Imports: {imports}")

    with open(os.path.join(project_dir, ".dev", "project.json"), "r", encoding="utf-8") as config_file:
        project_config = json.load(config_file)

    imports = list(set(imports + project_config.get("import_dir", [])))
    import_projects = project_config.get("import_projects", [])
    if import_projects:
        for project in import_projects:
            if isinstance(project, dict):
                project = project["path"]
            if project in loaded_projects:
                print(f"Project {project} already loaded. Skipping.")
                continue

            loaded_projects.append(project)
            imports = list(set(imports + get_project_imports(project, loaded_projects)))

    return imports


def coerce_preprocessor_imports(config):
    preprocessor_imports = config.get("preprocessor_imports", [])

    if isinstance(preprocessor_imports, str):
        return [preprocessor_imports]
    if not isinstance(preprocessor_imports, list):
        print("Preprocessor imports must be a list of directories.")
        raise SystemExit(1)

    return preprocessor_imports


def resolve_import_dirs(config):
    import_dir = config.get("import_dir", DEFAULT_IMPORT)
    if not isinstance(import_dir, list):
        import_dir = [import_dir]

    import_projects = config.get("import_projects", [])
    print(f"Import projects: {import_projects}")

    for project in import_projects:
        if isinstance(project, dict):
            project = project["path"]
        import_dir = list(set(import_dir + get_project_imports(project)))

    print(f"Importing from {import_dir}")
    return import_dir


def resolve_config(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config:
        config = load_config(args.config)
        if not config and not args.save_config:
            print(f"Config {args.config} does not exist. Use --save-config to create it.")
            raise SystemExit()
    else:
        config = {}

    config = merge_config(args, config)

    if args.save_config:
        save_config(args.config, config)

    verbose = bool(config.get("verbose", args.verbose))
    if verbose:
        pretty_config = json.dumps(config, indent=4)
        print(f"Using config:\n{pretty_config}")

    build_dir = os.path.abspath(args.build_dir if args.build_dir else config.get("build_dir", "build"))
    output_dir = verify_or_create_directory("output", config.get("output_dir", DEFAULT_OUTPUT))

    return BuildConfig(
        args=args,
        values=config,
        verbose=verbose,
        project_namespace=config.get("project_namespace"),
        preprocessor_imports=coerce_preprocessor_imports(config),
        import_dir=resolve_import_dirs(config),
        output_dir=output_dir,
        copy_source_to=config.get("copy_source_to"),
        assets_dir=config.get("assets_dir"),
        assets=config.get("assets", []),
        extras=config.get("extras", []),
        compiler_path=config.get("compiler_path", CONFIG_DEFAULTS["compiler_path"]),
        build_dir=build_dir,
    )