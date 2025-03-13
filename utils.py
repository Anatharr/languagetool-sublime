
import sublime
import itertools
import traceback
import fnmatch

# Problem manipulation functions

_PROBLEMS = {}
def save_problems(view, problems):
    global _PROBLEMS
    view_id = view.id()
    if view_id in _PROBLEMS and problems == []:
        del _PROBLEMS[view_id]
    else:
        _PROBLEMS[view_id] = problems

def get_problems(view):
    return _PROBLEMS[view.id()] if view.id() in _PROBLEMS else []

def shift_offset(problem, shift):
    """Shift problem offset by `shift`."""
    problem['offset'] += shift
    return problem

def get_region_for_problem(problem):
    """Returns a Region object corresponding to problem text."""
    length = problem['length']
    offset = problem['offset']
    return sublime.Region(offset, offset + length)

def region_contains(region, problem):
    """Returns True if problem text is inside region."""
    reg = get_region_for_problem(problem)
    return region.contains(reg)

def is_ignored(view, point):
    """Return True if any scope at given point is ignored."""
    scope_string = view.scope_name(point)
    scopes = scope_string.split()
    ignored_scopes = get_settings().get('ignored-scopes')
    return cross_match(scopes, ignored_scopes, fnmatch.fnmatch)

def parse_match(match):
    """Parse a match object.

    Args:
      match (dict): match object returned by LanguageTool Server.

    Returns:
      dict: problem object.
    """
    problem = {
        'category': match['rule']['category']['name'],
        'message': match['message'],
        'replacements': [r['value'] for r in match['replacements']],
        'rule': match['rule']['id'],
        'urls': [w['value'] for w in match['rule'].get('urls', [])],
        'offset': match['offset'],
        'length': match['length']
    }

    return problem


# Miscellaneous functions

def find_by_id(haystack, needle):
    try:
        return next(filter(lambda x:needle == (x['id'] if type(x) is dict else x.id()), haystack))
    except StopIteration:
        return None

def get_caller():
    print(''.join(traceback.format_stack()))

def get_settings():
    settings = sublime.load_settings('LanguageTool.sublime-settings')
    return settings

def log(*args):
    if get_settings().get('debug'):
        print("LanguageTool:", *args)

def set_status_bar(message):
    """Change status bar message."""
    sublime.status_message(message)

def compose(f1, f2):
    """Compose two functions."""
    def inner(*args, **kwargs):
        return f1(f2(*args, **kwargs))
    return inner

def cross_match(list1, list2, predicate):
    """Cross match items from two lists using a predicate.

    Args:
      list1 (list): list 1.
      list2 (list): list 2.

    Returns:
      True if predicate(x, y) is True for any x in list1 and y in list2,
      False otherwise.

    """
    return any(predicate(x, y) for x, y in itertools.product(list1, list2))
