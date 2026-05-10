import ply.lex as lex

# Tokens definition for the lexer
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

# States
states = (
    ('flag', 'exclusive'),
    ('macrobody', 'exclusive'),
)

# Regular expression rules for tokens in the INITIAL state

def t_DEFINE(t):
    r'\$DEFINE\b'
    return t

def t_DEFINE_MACRO(t):
    r'\$DEFINE_MACRO'
    t.lexer.in_macro_definition = True  # Set the flag to indicate we're in a macro definition
    return t

def t_MACRO(t):
    r'\$MACRO'
    return t

def t_IMPORTS(t):
    r'\$IMPORTS'
    return t

def t_LPAREN(t):
    r'\('
    return t

def t_RPAREN(t):
    r'\)'
    return t

def t_EQUALS(t):
    r'='
    return t

def t_COMMA(t):
    r','
    return t

def t_LBRACKET(t):
    r'\['
    t.lexer.push_state('flag')  # Switch to 'flag' state
    return t

def t_RBRACKET(t):
    r'\]'
    t.lexer.pop_state()
    return t

def t_DOLLAR_IDENTIFIER(t):
    r'\$[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_:]*'
    return t

def t_NUMBER(t):
    r'0x[0-9a-fA-F]+|\d+'
    return t

def t_STRING(t):
    r'"(\\.|[^"])*"'  # Match strings in double quotes
    t.value = t.value[1:-1]  # Remove the quotes
    return t

def t_LCURLY(t):
    r'\{'
    if getattr(t.lexer, 'in_macro_definition', False):
        t.lexer.push_state('macrobody')  # Enter macrobody state
        t.lexer.in_macro_definition = False  # Reset the flag
    return t

def t_RCURLY(t):
    r'\}'
    return t

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Token rules for the 'flag' state
def t_flag_RBRACKET(t):
    r'\]'
    t.lexer.pop_state()  # Return to INITIAL state
    return t

def t_flag_COMMA(t):
    r','
    return t

def t_flag_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

t_flag_ignore = ' \t'

def t_flag_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Token rules for the 'macrobody' state

def t_macrobody_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_macrobody_ANY_TEXT(t):
    r'(.|\n)+?(?=\})'
    t.type = 'ANY_TEXT'
    return t

def t_macrobody_RCURLY(t):
    r'\}'
    t.lexer.pop_state()
    return t

t_macrobody_ignore = ''

def t_macrobody_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Illegal character '{t.value[0]}', line {t.lineno}")
    t.lexer.skip(1)

def t_flag_error(t):
    print(f"Illegal character in flag state '{t.value[0]}', line {t.lineno}")
    t.lexer.skip(1)

def t_macrobody_error(t):
    print(f"Illegal character in macrobody state '{t.value[0]}', line {t.lineno}")
    t.lexer.skip(1)

lexer = lex.lex()
lexer.in_macro_definition = False  # Initialize the flag
