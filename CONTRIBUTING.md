# Contributing to ComfyUI Custom Nodes

First of all, thank you for considering contributing to this project! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

* Check if the bug has already been reported in the [Issues](https://github.com/EricRollei/AAA_Metadata_System/issues)
* If not, create a new issue with a descriptive title
* Include steps to reproduce, expected behavior, actual behavior, and environment details
* Include screenshots if applicable

### Suggesting Features

* Check if the feature has already been requested in the [Issues](https://github.com/EricRollei/AAA_Metadata_System/issues)
* If not, create a new issue with a descriptive title prefixed with [Feature Request]
* Clearly describe the feature and why it would be valuable
* Include examples of how the feature might work

### Code Contributions

#### Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/AAA_Metadata_System.git
   cd AAA_Metadata_System
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt  # if available
   ```

#### Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes following the coding standards

3. Test your changes thoroughly
   * Ensure existing functionality is not broken
   * Test with various inputs and edge cases
   * Verify the node works as expected within ComfyUI

4. Commit your changes:
   ```bash
   git commit -m "Description of your changes"
   ```

5. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request from your fork to the original repository

#### Coding Standards

* Use consistent formatting with the rest of the codebase
* Include appropriate docstrings and comments
* Follow PEP 8 guidelines for Python code
* Each new node should include:
  * Proper type annotations
  * Clear documentation of inputs and outputs
  * Error handling for invalid inputs

#### Adding a New Node

1. Create a new Python file in the appropriate directory
2. Use the license header template at the top of the file
3. Implement the node following ComfyUI's node architecture
4. Document the node in the README.md
5. If appropriate, add examples demonstrating the node's use

## Pull Request Process

1. Update the README.md with details of your changes if applicable
2. Add your new node to the node catalog if applicable
3. Update any examples or documentation to reflect your changes
4. The maintainer will review your PR and may request changes
5. Once approved, your PR will be merged

## License Considerations

* By contributing to this project, you agree that your contributions will be licensed under the project's dual license
* Ensure any libraries or code you include is compatible with the existing licenses

Thank you for your contributions!
