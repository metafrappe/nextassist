"""Focused regressions for the v16 ports. External AI/AWS calls are simulated."""
import importlib
import io
import queue
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.model.base_document import get_controller


def run(app):
    assert app in frappe.get_installed_apps()
    modules = frappe.get_all('Module Def', filters={'app_name': app}, pluck='name')
    doctypes = frappe.get_all('DocType', filters={'module': ['in', modules]}, pluck='name')
    for doctype in doctypes:
        frappe.get_meta(doctype)
        get_controller(doctype)
    globals()['check_' + app]()
    print({'app': app, 'controllers': len(doctypes), 'regressions': 'passed'})


def check_nextassist():
    from claude_agent_sdk import AssistantMessage, TextBlock
    from nextassist.ai import claude_code_provider as module
    from nextassist.database.pool import test_connection
    from nextassist.database.settings_db import get_settings, save_settings
    assert test_connection()
    save_settings({'enable_tool_calling': True, 'enable_file_uploads': False})
    assert not get_settings()['enable_file_uploads']
    save_settings({'enable_tool_calling': True, 'enable_file_uploads': True})
    provider = module.ClaudeCodeProvider(SimpleNamespace(get_password=lambda key: 'ci-placeholder'))
    options = provider._build_options('test-model', 'test system')
    assert options.model == 'test-model' and options.system_prompt == 'test system'
    assert options.env['ANTHROPIC_API_KEY'] == 'ci-placeholder'
    async def mock_query(*, prompt, options):
        assert prompt == 'Hello'
        yield AssistantMessage(content=[TextBlock(text='Merhaba')], model='test-model')
    with patch.object(module, 'query', mock_query):
        response = provider.chat_completion([{'role': 'user', 'content': 'Hello'}], model='test-model')
    assert response['content'] == 'Merhaba'
