from bgs_tools.constellation.preprocessor.nodes import EmittedFile


def emit_source_file(source_file):
    emitted_text = source_file.body_text()

    for generated_function in source_file.generated_functions:
        emitted_text = emitted_text.rstrip() + "\n\n" + generated_function

    return EmittedFile(path=source_file.file_path, text=emitted_text, kind="primary")