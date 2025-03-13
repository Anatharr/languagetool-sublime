
import sublime
from .utils import *

def move_caret(view, i, j):
    """Select character range [i, j] in view."""
    target = view.text_point(0, i)
    view.sel().clear()
    view.sel().add(sublime.Region(target, target + j - i))


def select_problem(view, problem):
    reg = view.get_regions(problem['regionKey'])[0]
    move_caret(view, reg.a, reg.b)
    view.show_at_center(reg)
    show_problem(view, problem)


def is_problem_solved(view, problem):
    """Return True if a language problem has been resolved.

    A problem is considered resolved if either:

    1. its region has zero length, or
    2. its contents have been changed.
    """
    pb_regions = view.get_regions(problem['id'])
    if len(pb_regions) == 0:
        return False
    region = pb_regions[0]
    return region.empty() or (view.substr(region) != problem['originalContent'])


def show_problem(view, p):
    """Show problem description and suggestions."""

    log("show_problem", p)

    msg = p['message']
    if p['replacements']:
        msg += '\n\nSuggestion(s): ' + ', '.join(p['replacements'])
    if p['urls']:
        msg += '\n\nMore Info: ' + '\n'.join(p['urls'])

    view.show_popup(msg)

def show_panel_text(text):
    window = sublime.active_window()
    if _is_ST2():
        pt = window.get_output_panel("languagetool")
        pt.set_read_only(False)
        edit = pt.begin_edit()
        pt.insert(edit, pt.size(), text)
        window.run_command("show_panel", {"panel": "output.languagetool"})
    else:
        window.run_command('set_language_tool_panel_text', {'str': text})

def choose_suggestion(view, p, replacements, choice):
    """Handle suggestion list selection."""
    problems = view.__dict__.get("problems", [])
    if choice != -1:
        r = view.get_regions(p['regionKey'])[0]
        view.run_command('insert', {'characters': replacements[choice]})
        c = r.a + len(replacements[choice])
        move_caret(view, c, c)  # move caret to end of region
        view.run_command("goto_next_language_problem")
    else:
        select_problem(view, p)


def get_equal_problems(problems, x):
    """Find problems with same category and content as a given problem.

    Args:
      problems (list): list of problems to compare.
      x (dict): problem object to compare with.

    Returns:
      list: list of problems equal to x.

    """

    def is_equal(prob1, prob2):
        same_category = prob1['category'] == prob2['category']
        same_content = prob1['orgContent'] == prob2['orgContent']
        return same_category and same_content

    return [problem for problem in problems if is_equal(problem, x)]


def handle_language_selection(ind, view):
    key = 'language_tool_language'
    if ind == 0:
        view.settings().erase(key)
    else:
        selected_language = view.languages[ind][1]
        view.settings().set(key, selected_language)


def correct_problem(view, edit, problem, replacements):

    def clear_and_advance():
        clear_region(view, problem['regionKey'])
        move_caret(view, next_caret_pos, next_caret_pos)  # advance caret
        view.run_command("goto_next_language_problem")

    if len(replacements) > 1:
        def callback_fun(i):
            choose_suggestion(view, problem, replacements, i)
            clear_and_advance()
        view.window().show_quick_panel(replacements, callback_fun)

    else:
        region = view.get_regions(problem['regionKey'])[0]
        view.replace(edit, region, replacements[0])
        next_caret_pos = region.a + len(replacements[0])
        clear_and_advance()

def ignore_problem(p, v, edit):
    clear_region(v, p['regionKey'])
    v.insert(edit, v.size(), "")  # dummy edit to enable undoing ignore

def load_ignored_rules():
    ignored_rules_file = 'LanguageToolUser.sublime-settings'
    settings = sublime.load_settings(ignored_rules_file)
    return settings.get('ignored', [])

def save_ignored_rules(ignored):
    ignored_rules_file = 'LanguageToolUser.sublime-settings'
    settings = sublime.load_settings(ignored_rules_file)
    settings.set('ignored', ignored)
    sublime.save_settings(ignored_rules_file)

def clear_region(view, region_key):
    r = view.get_regions(region_key)[0]
    dummyRg = sublime.Region(r.a, r.a)
    hscope = get_settings().get("highlight-scope", "comment")
    view.add_regions(region_key, [dummyRg], hscope, "", sublime.DRAW_OUTLINED)


# _HIGHLIGHTED_REGIONS = {}
# def add_highlight_region(view, region_key, problem):
#     global _HIGHLIGHTED_REGIONS
#     problem['regionKey'] = region_key
#     view_id = view.id()

#     if view_id not in _HIGHLIGHTED_REGIONS:
#         _HIGHLIGHTED_REGIONS[view_id] = []

#     _HIGHLIGHTED_REGIONS[view_id][region_key] = region

#     view.add_regions(region_key, [], "text", "",
#                           sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

# def remove_highlight_region(view, region_key):
#     view.erase_regions(region_key)
#     if view.id() in _HIGHLIGHTED_REGIONS and re[view_id]:
#         pass

def recompute_highlights(view):
    problems = get_problems(view)
    for problem in list(problems):
        region = get_region_for_problem(problem)
        if is_problem_solved(view, problem):
            log("RECOMPUTE", "removing solved problem", problem['id'])
            view.erase_regions(problem['id'])
            problems.remove(problem)
        else:
            view.add_regions(problem['id'], [region], "text", "",
                                sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)
    save_problems(view, problems)