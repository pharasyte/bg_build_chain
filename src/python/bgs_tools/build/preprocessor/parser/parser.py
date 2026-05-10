import ply.yacc as yacc

from bgs_tools.build.preprocessor.lexer import lexer

tokens = (
    'STRING',
    'NUMBER',
    'IDENTIFIER',
    'DOLLAR_IDENTIFIER',
    'EQUALS',
    'COMMA',
    'LCURLY',
    'RCURLY',
    'LBRACKET',
    'RBRACKET',
    'LPAREN',
    'RPAREN',
    'DEFINE_MACRO',
    'DEFINE',
    'MACRO',
    'IMPORTS',
    'ANY_TEXT',
)

def p_program(p):
    '''program : statements'''
    pass

def p_statements(p):
    '''statements : statements statement
                  | statement'''
    pass

def p_statement(p):
    '''statement : imports_statement
                 | define_block
                 | define_macro
                 | macro_call'''
    pass

def p_imports_statement(p):
    '''imports_statement : IMPORTS LCURLY import_list RCURLY'''
    p.parser.results['imports'] = p[3]
    print(f"Parsed imports: {p.parser.results['imports']}")

def p_import_list(p):
    '''import_list : import_list import_item
                   | import_item'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_import_item(p):
    '''import_item : IDENTIFIER'''
    p[0] = p[1]

def p_define_block(p):
    '''define_block : DEFINE LCURLY variable_list RCURLY'''
    p.parser.results['vars'].extend(p[3])
    print(f"Variables: {[p.parser.results['vars']]}")

def p_optional_flag(p):
    '''optional_flag : IDENTIFIER
                     | empty'''
    p[0] = p[1] if len(p) == 2 else None

def p_variable_list(p):
    '''variable_list : variable_list variable_definition
                     | variable_definition'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_variable_definition(p):
    '''variable_definition : IDENTIFIER EQUALS value flag_list_opt'''
    var_name = p[1]
    value = p[3]
    flags = p[4]

    var_type = 'String' if var_name.startswith('s') else \
               'Int' if var_name.startswith('i') else \
               'Bool' if var_name.startswith('b') else \
               'Float' if var_name.startswith('f') else 'Unknown'

    p[0] = {'name': var_name[1:], 'type': var_type, 'value': value, 'flags': flags}

def p_flag_list_opt(p):
    '''flag_list_opt : LBRACKET flag_list RBRACKET
                     | empty'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = []

def p_flag_list(p):
    '''flag_list : flag_list COMMA IDENTIFIER
                 | flag_list IDENTIFIER
                 | IDENTIFIER'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_define_macro(p):
    '''define_macro : DEFINE_MACRO IDENTIFIER LPAREN macro_params RPAREN LCURLY macro_body RCURLY'''
    print("Parsing macro definition")
    macro_name = p[2]
    params = p[4]
    body = p[7]
    # Store the macro definition
    p.parser.results['macros'].append({'name': macro_name, 'params': params, 'body': body})
    print(f"Defined macro: {macro_name} with params {params}")
    print(f"Macro body:\n{body}")

def p_macro_body(p):
    '''macro_body : macro_body ANY_TEXT
                  | ANY_TEXT'''
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1]

def p_macro_params(p):
    '''macro_params : macro_params COMMA DOLLAR_IDENTIFIER
                    | DOLLAR_IDENTIFIER
                    | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1]:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_macro_call(p):
    '''macro_call : MACRO IDENTIFIER LPAREN macro_args RPAREN'''
    macro_name = p[2]
    args = p[4]
    # Handle the macro call as needed
    p.parser.results['macro_calls'].append({'name': macro_name, 'args': args})
    print(f"Macro call: {macro_name} with args {args}")

def p_macro_args(p):
    '''macro_args : macro_args COMMA value
                  | value
                  | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1]:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_value(p):
    '''value : STRING
             | NUMBER
             | IDENTIFIER
             | DOLLAR_IDENTIFIER'''
    p[0] = p[1]

def p_empty(p):
    '''empty :'''
    p[0] = []

def p_error(p):
    if p:
        print(f"Syntax error at '{p.value}', line {p.lineno}, {p}")
    else:
        print("Syntax error at EOF")

def get_parser():
    parser = yacc.yacc()
    parser.results = {
        'imports': [],
        'vars': [],
        'macros': [],
        'macro_calls': []
    }
    
    return parser