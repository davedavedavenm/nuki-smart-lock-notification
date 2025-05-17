"""
Dark mode initializer for Nuki Smart Lock Dashboard
Ensures dark mode is set as default theme for all sessions
"""

def init_app(app):
    # Set dark mode as default for all sessions
    @app.before_request
    def set_default_theme():
        import os
        from flask import session, request
        
        # Always ensure theme is set
        if "theme" not in session or not session.get("theme"):
            # Use environment variable or default to dark mode
            default_theme = os.environ.get('DEFAULT_THEME', 'dark')
            session["theme"] = default_theme
        
        # Force dark mode for all new sessions
        if request.endpoint == 'login' and 'logged_in' not in session:
            session["theme"] = 'dark'
    
    # Add a template context processor to always provide theme
    @app.context_processor
    def inject_theme():
        from flask import session
        return {'theme': session.get('theme', 'dark')}
