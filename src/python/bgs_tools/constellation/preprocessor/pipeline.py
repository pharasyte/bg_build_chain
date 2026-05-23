from bgs_tools.constellation.preprocessor.emitter import emit_source_file
from bgs_tools.constellation.preprocessor.lift import lift_source_file
from bgs_tools.constellation.preprocessor.nodes import TranspileResult
from bgs_tools.constellation.preprocessor.transforms import apply_transforms
from bgs_tools.constellation.preprocessor.tree_sitter_parser import parse_with_tree_sitter


def transpile_source(source_text, file_path, context=None):
    parser_info = parse_with_tree_sitter(source_text)
    source_file = lift_source_file(source_text, file_path, parser_info=parser_info)
    macro_calls = apply_transforms(source_file, context=context)
    primary = emit_source_file(source_file)

    source_maps = []
    if primary.text != source_text:
        source_maps.append(
            {
                "kind": "staged-primary",
                "source_path": file_path,
                "emitted_path": primary.path,
                "note": "Generated line mapping is not yet expanded beyond primary staged-file output.",
            }
        )

    return TranspileResult(
        source_path=file_path,
        primary=primary,
        macro_calls=macro_calls,
        parser=parser_info,
        source_maps=source_maps,
    )