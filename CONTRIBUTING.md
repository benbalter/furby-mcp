# Contributing to Furby MCP

Thank you for your interest in contributing to Furby MCP! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/furby-mcp.git
   cd furby-mcp
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Build the project:
   ```bash
   npm run build
   ```

## Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes to the TypeScript source files in `src/`

3. Build and test your changes:
   ```bash
   npm run build
   ```

4. Test the MCP server manually if possible with a Furby Connect device

5. Commit your changes with a clear commit message:
   ```bash
   git commit -m "Add feature: description of your changes"
   ```

6. Push to your fork and create a Pull Request

## Code Style

- Use TypeScript for all new code
- Follow the existing code style
- Add JSDoc comments for public methods
- Use meaningful variable and function names
- Keep functions focused and single-purpose

## Testing

While we don't have automated tests yet, please test your changes:
- Build successfully without errors
- MCP server starts and responds to initialize
- Tools work as expected (if you have access to a Furby Connect)

## Areas for Contribution

Here are some areas where contributions would be especially welcome:

### Documentation
- More detailed action mappings
- Setup guides for different operating systems
- Troubleshooting guides
- Video tutorials

### Features
- Add more Furby control tools
- Implement DLC flashing support
- Add sensor reading capabilities
- Better error messages and diagnostics
- Support for multiple connected Furbies

### Testing
- Unit tests for FurbyController
- Integration tests for MCP tools
- Mock Furby device for testing

### Examples
- Example VS Code configurations
- Example automation scripts
- Example use cases

## Furby Protocol Research

If you discover new Furby commands or behaviors:
1. Document them thoroughly
2. Test them to ensure they work reliably
3. Add them to ACTIONS.md
4. Consider contributing back to the [bluefluff project](https://github.com/Jeija/bluefluff)

## Pull Request Process

1. Update documentation if you're adding features
2. Ensure your code builds without errors
3. Write a clear PR description explaining your changes
4. Link any related issues
5. Be responsive to feedback and questions

## Questions?

If you have questions or need help:
- Open an issue on GitHub
- Check the [bluefluff documentation](https://github.com/Jeija/bluefluff)
- Review the MCP SDK documentation

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Remember we're all here because we love Furby! 🤖

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
