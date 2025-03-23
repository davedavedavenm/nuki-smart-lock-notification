# Contributing to the Nuki Smart Lock Notification System

Thank you for considering contributing to this project! Here are some guidelines to help you get started.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. This includes:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with the following information:

1. A clear, descriptive title
2. A detailed description of the bug
3. Steps to reproduce the bug
4. Expected behavior
5. Screenshots (if applicable)
6. Environment information:
   - OS version
   - Python version
   - Raspberry Pi model
   - Nuki lock model

### Suggesting Enhancements

If you have an idea for an enhancement, please open an issue with:

1. A clear, descriptive title
2. A detailed description of the enhancement
3. The motivation behind the enhancement
4. Any potential implementation details you can think of

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Make your changes
4. Run the tests (if available)
5. Make sure your code follows the project's style guide
6. Submit a pull request

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nuki-smart-lock-notification-system.git
cd nuki-smart-lock-notification-system
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create example config files:
```bash
mkdir -p config
cp config/config.ini.example config/config.ini
cp config/credentials.ini.example config/credentials.ini
```

5. Customize the config files with your own settings.

## Testing

Before submitting a pull request, please test your changes:

1. Run the sanitization check:
```bash
python sanitize_check.py
```

2. Test the core functionality:
```bash
python scripts/nuki_monitor.py
```

3. Test the web interface (if applicable):
```bash
python web/app.py
```

## Style Guide

This project follows PEP 8 style guidelines for Python code. Please make sure your code adheres to these guidelines.

## Security Considerations

When contributing, please be mindful of security:

- Never commit API tokens, passwords, or other sensitive information
- Follow the principle of least privilege
- Validate user input
- Use secure communication (HTTPS, SSL/TLS)

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.
