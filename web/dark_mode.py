"""
Dark mode initializer for Nuki Smart Lock Dashboard
Ensures dark mode is set as default theme for all sessions
"""

def init_app(app):
    # Set dark mode as default for all sessions
    @app.before_request
    def set_default_theme():
        import os
        from flask import session
        if "theme" not in session:
            # Use environment variable or default to dark mode
            default_theme = os.environ.get('DEFAULT_THEME', 'dark')
            session["theme"] = default_theme
