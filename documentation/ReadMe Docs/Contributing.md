# Contributing to Metadata System for ComfyUI

Thank you for your interest in contributing to the Metadata System for ComfyUI! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Code Contributions](#code-contributions)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)
- [Testing](#testing)
- [Licensing](#licensing)

## Code of Conduct

This project adheres to a Code of Conduct that establishes how the community interacts. By participating, you are expected to uphold this code. Please report unacceptable behavior to [eric@historic.camera](mailto:eric@historic.camera).

## Getting Started

1. Fork the repository
2. Clone your fork to your local machine
3. Set up the development environment (see [Development Setup](#development-setup))
4. Create a branch for your changes
5. Make your changes
6. Submit a pull request

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue using the bug report template. Include as much detail as possible:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, ComfyUI version, etc.)

### Suggesting Enhancements

Have an idea for an enhancement? Create an issue using the feature request template. Include:

- A clear and descriptive title
- A detailed description of the proposed enhancement
- The motivation behind the enhancement
- Possible implementation details (if known)

### Code Contributions

Code contributions are welcome through pull requests. Please follow these steps:

1. Check existing issues and pull requests to avoid duplicating work
2. Create a new branch for your changes
3. Follow the [Coding Standards](#coding-standards)
4. Add tests for your changes
5. Update documentation as needed
6. Submit a pull request

## Development Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/YourUsername/Metadata_system.git
   cd Metadata_system
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install optional dependencies for full functionality:
   ```bash
   # Install PyExiv2 (if possible)
   pip install pyexiv2
   
   # Install ExifTool (platform-specific)
   # See INSTALLATION.md for details
   ```

5. Run tests to verify your setup:
   ```bash
   pytest
   ```

## Pull Request Process

1. Update your branch with the latest changes from the main repository
2. Ensure your code passes all tests
3. Update documentation for any changed functionality
4. Submit your pull request with a clear description of the changes
5. Address any feedback from the code review

Pull requests will be merged once they have been reviewed and approved by a project maintainer.

## Coding Standards

Please follow these coding standards:

- Use [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Include comprehensive docstrings for all classes and methods
- Use type hints for function parameters and return values
- Write clear, descriptive comments explaining complex logic
- Use meaningful variable and function names
- Keep functions short and focused on a single responsibility
- Handle errors gracefully with appropriate exception handling

Example:

```python
def process_metadata(self, filepath: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process metadata and return enhanced version.
    
    Args:
        filepath: Path to the original file
        metadata: Original metadata to process
        
    Returns:
        Enhanced metadata with additional information
        
    Raises:
        FileNotFoundError: If filepath does not exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
        
    # Process metadata
    result = metadata.copy()
    
    # Add processing logic here
    
    return result
```

## Documentation

Good documentation is essential. When contributing, please:

- Update docstrings for any changed/added functions or classes
- Update README.md for any user-facing changes
- Update API_REFERENCE.md for any API changes
- Create/update examples to demonstrate new features

## Testing

Write tests for all new features and bug fixes. Tests should be:

- Located in the `tests/` directory
- Named with a `test_` prefix (e.g., `test_embedded_handler.py`)
- Written using pytest
- Thorough enough to cover edge cases

Example:

```python
def test_read_metadata_nonexistent_file():
    """Test reading metadata from a nonexistent file."""
    handler = EmbeddedMetadataHandler(debug=True)
    result = handler.read_metadata("nonexistent_file.jpg")
    assert result == {}

def test_write_metadata_valid():
    """Test writing metadata to a valid file."""
    handler = EmbeddedMetadataHandler(debug=True)
    
    # Create a test image
    from PIL import Image
    test_img = Image.new('RGB', (100, 100), color='red')
    test_file = "test_write.jpg"
    test_img.save(test_file)
    
    metadata = {'basic': {'title': 'Test Image'}}
    result = handler.write_metadata(test_file, metadata)
    
    assert result is True
    
    # Cleanup
    os.remove(test_file)
```

## Licensing

By contributing to this project, you agree that your contributions will be licensed under the project's dual license. Please review the LICENSE file in the repository for details.

Thank you for contributing to the Metadata System for ComfyUI!