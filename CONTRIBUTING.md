# Contributing to Furby DLC Editor

Thank you for your interest in contributing to the Furby DLC Editor! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/furby-mcp.git`  
   (Replace `YOUR_USERNAME` with your GitHub username)
3. Install dependencies: `pip install -r requirements.txt`
4. Create a new branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Install in development mode
pip install -e .

# Run tests
python -m unittest test_dlc_editor.py -v
```

## Testing

Before submitting a pull request, please ensure:

1. All existing tests pass
2. New features include appropriate tests
3. Code follows Python best practices (PEP 8)

Run tests with:
```bash
python -m unittest test_dlc_editor.py -v
```

## Code Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise

## Submitting Changes

1. Commit your changes with clear, descriptive messages
2. Push to your fork
3. Submit a pull request with:
   - Clear description of changes
   - Any relevant issue numbers
   - Test results

## Areas for Contribution

We welcome contributions in the following areas:

### High Priority
- Add support for converting standard audio formats (WAV, MP3) to A18
- Implement a GUI interface
- Add more comprehensive tests
- Improve error handling and validation

### Medium Priority
- Document the DLC file format in more detail
- Add support for modifying motor animations
- Create visual tools for sprite editing
- Add batch processing capabilities

### Documentation
- Improve README with more examples
- Add tutorials for common tasks
- Document the internal DLC structure
- Create video tutorials

## Questions?

If you have questions or need help, please:
- Open an issue with the `question` label
- Check existing issues and discussions
- Review the [original Furby research](https://github.com/ctxis/Furby)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming community for all contributors.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (GNU GPL v2+).

## Acknowledgments

This project is based on the reverse engineering work by Ed Locard (@L0C4RD) and the Context IS team. Please see the [original Furby project](https://github.com/ctxis/Furby) for more details.
