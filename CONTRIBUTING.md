# Contributing to S-Expression Agent System

Thank you for your interest in contributing to the S-Expression Agent System! This document provides guidelines for contributing to the project.

## 🌐 Languages / 言語

- **English** (This file)
- **[日本語版 CONTRIBUTING](CONTRIBUTING_JP.md)** *(Coming soon)*

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Git
- Basic understanding of S-expressions and LLM concepts

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/s_style_agent.git
   cd s-style-agent
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Run tests to ensure everything works**
   ```bash
   uv run python -c "from s_style_agent.config.settings import settings; print('✅ Setup successful')"
   ```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - OS and Python version
   - LLM configuration
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant S-expressions

### Suggesting Features

1. Check existing feature requests
2. Use the feature request template
3. Describe:
   - The problem you're trying to solve
   - Your proposed solution
   - Any new S-expression syntax needed
   - Implementation ideas (optional)

### Code Contributions

#### Areas for Contribution

- **Core Engine**: S-expression evaluation, parsing improvements
- **Tool System**: New tools, tool integrations
- **MCP Integration**: New MCP servers, protocol improvements
- **CLI/API**: User interface enhancements
- **Documentation**: Guides, examples, translations
- **Testing**: Test coverage improvements

#### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation

3. **Test your changes**
   ```bash
   # Run basic functionality tests
   uv run python -c "
   from s_style_agent.core.parser import parse_s_expression
   from s_style_agent.core.evaluator import ContextualEvaluator, Environment
   
   # Your test code here
   print('✅ Tests passed')
   "
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "Add: Brief description of your changes
   
   - Specific change 1
   - Specific change 2
   
   Closes #issue-number"
   ```

5. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Code Style Guidelines

- **Python**: Follow PEP 8
- **S-expressions**: Use consistent formatting and naming
- **Comments**: Write clear, concise comments in English
- **Docstrings**: Use clear docstrings for all public functions

#### Adding New S-Expression Operations

When adding new S-expression operations:

1. **Update the evaluator** (`s_style_agent/core/evaluator.py`)
2. **Add corresponding tests**
3. **Update documentation** with examples
4. **Consider error handling** and edge cases

Example:
```python
elif op == 'your-new-op':
    # Validate arguments
    if len(args) != 2:
        raise TypeError(f"your-new-op requires 2 arguments, got {len(args)}")
    
    # Evaluate arguments
    arg1 = self._evaluate_basic(args[0], env)
    arg2 = self._evaluate_basic(args[1], env)
    
    # Implement functionality
    return your_implementation(arg1, arg2)
```

#### Adding New Tools

1. **Create tool class** in `s_style_agent/tools/`
2. **Register the tool** in `builtin_tools.py`
3. **Add tests** in `s_style_agent/tests/`
4. **Update documentation**

### Documentation Contributions

#### Translation Guidelines

We welcome translations! Please:

1. Create `README_[LANG_CODE].md` files
2. Maintain the same structure as the original
3. Translate explanatory text, keep code examples unchanged
4. Test all code examples work correctly
5. Update `docs/README_languages.md`

#### Documentation Standards

- **Clear examples** for all features
- **Step-by-step instructions** for setup
- **Troubleshooting sections** for common issues
- **API documentation** for developers

## Testing

### Running Tests

```bash
# Basic import tests
uv run python -c "from s_style_agent.config.settings import settings"

# S-expression evaluation tests
uv run python -c "
from s_style_agent.core.parser import parse_s_expression
from s_style_agent.core.evaluator import ContextualEvaluator, Environment

evaluator = ContextualEvaluator()
env = Environment()
result = evaluator._evaluate_basic(parse_s_expression('(+ 2 3)'), env)
assert result == 5
print('✅ Basic tests passed')
"
```

### Test Coverage

- **Parser tests**: S-expression parsing edge cases
- **Evaluator tests**: All S-expression operations
- **Tool tests**: Individual tool functionality
- **Integration tests**: End-to-end workflows
- **Configuration tests**: Environment variable handling

## Security Guidelines

- **Never commit API keys** or sensitive information
- **Use environment variables** for configuration
- **Validate all inputs** in S-expressions
- **Report security issues** privately to maintainers

## Community Guidelines

- **Be respectful** and inclusive
- **Help others** learn and contribute
- **Provide constructive feedback** in reviews
- **Share knowledge** and best practices

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check README and docs first

## Recognition

Contributors will be recognized in:
- Git commit history
- Release notes for significant contributions
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to making the S-Expression Agent System better! 🚀

*Generated with ❤️ by the community*