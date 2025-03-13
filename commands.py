"""
LanguageTool.py

This is a simple Sublime Text plugin for checking grammar. It passes buffer
content to LanguageTool (via http) and highlights reported problems.
"""

import sublime
import sublime_plugin
# import subprocess
# import os.path

from .utils import *
from .ui import *
from .languages import LANGUAGES
from . import server

class setLanguageToolPanelTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, str):
        window = sublime.active_window()
        pt = window.get_output_panel("languagetool")
        pt.settings().set("wrap_width", 0)
        pt.settings().set("word_wrap", True)
        pt.set_read_only(False)
        pt.run_command('insert', {'characters': str})
        window.run_command("show_panel", {"panel": "output.languagetool"})


class gotoNextLanguageProblemCommand(sublime_plugin.TextCommand):
    def run(self, edit, jump_forward=True):
        problems = get_problems(self.view)
        if len(problems) > 0:
            sel = self.view.sel()[0]
            if jump_forward:
                for p in problems:
                    r = self.view.get_regions(p['regionKey'])[0]
                    if (not is_problem_solved(self.view, p)) and (sel.begin() < r.a):
                        select_problem(self.view, p)
                        return
            else:
                for p in reversed(problems):
                    r = self.view.get_regions(p['regionKey'])[0]
                    if (not is_problem_solved(self.view, p)) and (r.a < sel.begin()):
                        select_problem(self.view, p)
                        return
        set_status_bar("no further language problems to fix")
        sublime.active_window().run_command("hide_panel", {
            "panel": "output.languagetool"
        })


class clearLanguageProblemsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        problems = get_problems(self.view)
        log("clear", problems, self.view.clones())
        for p in problems:
            self.view.erase_regions(p['regionKey'])
        problems = []
        recompute_highlights(self.view)
        # caretPos = self.view.sel()[0].end()
        # self.view.sel().clear()
        # move_caret(self.view, caretPos, caretPos)


class markLanguageProblemSolvedCommand(sublime_plugin.TextCommand):
    def run(self, edit, apply_fix):

        problems = get_problems(self.view)
        selected_region = self.view.sel()[0]

        # Find problem corresponding to selection
        for problem in problems:
            problem_region = self.view.get_regions(problem['regionKey'])[0]
            if problem_region == selected_region:
                break
        else:
            set_status_bar('no language problem selected')
            return

        next_caret_pos = problem_region.a
        replacements = problem['replacements']

        if apply_fix and replacements:
            # fix selected problem:
            correct_problem(self.view, edit, problem, replacements)

        else:
            # ignore problem:
            equal_problems = get_equal_problems(problems, problem)
            for p2 in equal_problems:
                ignore_problem(p2, self.view, edit)
            # After ignoring problem:
            move_caret(self.view, next_caret_pos, next_caret_pos)  # advance caret
            self.view.run_command("goto_next_language_problem")

# class startLanguageToolServerCommand(sublime_plugin.TextCommand):
#     """Launch local LanguageTool Server."""

#     def run(self, edit):

#         jar_path = get_settings().get('languagetool_jar')

#         if not jar_path:
#             show_panel_text("Setting languagetool_jar is undefined")
#             return

#         if not os.path.isfile(jar_path):
#             show_panel_text(
#                 'Error, could not find LanguageTool\'s JAR file (%s)'
#                 '\n\n'
#                 'Please install LT in this directory'
#                 ' or modify the `languagetool_jar` setting.' % jar_path)
#             return

#         sublime.status_message('Starting local LanguageTool server ...')

#         cmd = ['java', '-cp', jar_path, 'org.languagetool.server.HTTPServer', '--port', '8081']

#         if sublime.platform() == "windows":
#             p = subprocess.Popen(
#                 cmd,
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 shell=True,
#                 creationflags=subprocess.SW_HIDE)
#         else:
#             p = subprocess.Popen(
#                 cmd,
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE)


class changeLanguageToolLanguageCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.languages = LANGUAGES
        languageNames = [x[0] for x in self.view.languages]
        handler = lambda ind: handle_language_selection(ind, self.view)
        self.view.window().show_quick_panel(languageNames, handler)

class LanguageToolCommand(sublime_plugin.TextCommand):
    def run(self, edit, force_server=None):

        settings = get_settings()
        server_url = settings.get('server')
        # highlight_scope = settings.get('highlight-scope')

        selection = self.view.sel()[0] if self.view.sel() else None # first selection (ignore rest)
        everything = sublime.Region(0, self.view.size())
        check_region = everything if selection is None or selection.empty() else selection
        check_text = self.view.substr(check_region)

        self.view.run_command("clear_language_problems")

        language = self.view.settings().get('language_tool_language', 'auto')
        ignored_ids = [rule['id'] for rule in load_ignored_rules()]

        matches = server.getResponse(server_url, check_text, language,
                                       ignored_ids)
        log("MATCHES", matches)

        if matches == None:
            set_status_bar('Could not parse server response')
            return

        shifter = lambda problem: shift_offset(problem, check_region.a)
        get_problem = compose(shifter, parse_match)

        problems = [problem for problem in map(get_problem, matches)
                    if region_contains(check_region, problem) and not is_ignored(self.view, problem)]

        for index, problem in enumerate(problems):
            problem['originalContent'] = self.view.substr(get_region_for_problem(problem))
            problem['id'] = str(index)

        save_problems(self.view, problems)
        recompute_highlights(self.view)

# class DeactivateRuleCommand(sublime_plugin.TextCommand):
#     def run(self, edit):
#         ignored = load_ignored_rules()
#         problems = get_problems(self.view)
#         sel = self.view.sel()[0]
#         selected = [
#             p for p in problems
#             if sel.contains(self.view.get_regions(p['regionKey'])[0])
#         ]
#         if not selected:
#             set_status_bar('select a problem to deactivate its rule')
#         elif len(selected) == 1:
#             rule = {
#                 "id": selected[0]['rule'],
#                 "description": selected[0]['message']
#             }
#             ignored.append(rule)
#             ignoredProblems = [p for p in problems if p['rule'] == rule['id']]
#             for p in ignoredProblems:
#                 ignore_problem(p, self.view, edit)
#             problems = [p for p in problems if p['rule'] != rule['id']]
#             self.view.run_command("goto_next_language_problem")
#             save_ignored_rules(ignored)
#             set_status_bar('deactivated rule %s' % rule)
#         else:
#             set_status_bar('there are multiple selected problems;'
#                            ' select only one to deactivate')


# class ActivateRuleCommand(sublime_plugin.TextCommand):
#     def run(self, edit):
#         ignored = load_ignored_rules()
#         if ignored:
#             activate_callback_wrapper = lambda i: self.activate_callback(i)
#             ruleList = [[rule['id'], rule['description']] for rule in ignored]
#             self.view.window().show_quick_panel(ruleList,
#                                                 activate_callback_wrapper)
#         else:
#             set_status_bar('there are no ignored rules')

#     def activate_callback(self, i):
#         ignored = load_ignored_rules()
#         if i != -1:
#             activate_rule = ignored[i]
#             ignored.remove(activate_rule)
#             save_ignored_rules(ignored)
#             set_status_bar('activated rule %s' % activate_rule['id'])


class LanguageToolListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        # buffer text was changed, recompute region highlights
        recompute_highlights(view)

    def on_hover(self, view, point, hover_zone):
        if hover_zone == 1: # sublime.HoverZone.TEXT
            log("HOVER", view, get_problems(view), point, view.scope_name(point))