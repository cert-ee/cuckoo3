# Contributing to Cuckoo3

Thank you for your interest in contributing to **Cuckoo3**! Your contributions are invaluable and help make this project better for everyone.

## Table of Contents

- [Getting Started](#getting-started)
- [How You Can Contribute](#how-you-can-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Contributing Code](#contributing-code)
- [Development Guidelines](#development-guidelines)
  - [Coding Standards](#coding-standards)
  - [Commit Messages](#commit-messages)
  - [Testing](#testing)
- [Code of Conduct](#code-of-conduct)
- [License](#license)
- [Contact Us](#contact-us)

---

## Getting Started

- **Fork the Repository**: Click the "Fork" button at the top right corner of this page.
- **Clone Your Fork**: Clone your forked repository to your local machine.

  ```bash
  git clone https://github.com/your-username/cuckoo3.git
  ```

- **Set Upstream Remote**: Add the original repository as a remote to keep your fork updated.

  ```bash
  git remote add upstream https://github.com/cert-ee/cuckoo3.git
  ```

- **Create a Branch**: Create a new branch for your feature or bug fix.

  ```bash
  git checkout -b feature/your-feature-name
  ```

---

## How You Can Contribute

### Reporting Bugs

If you find a bug, please open an [issue](https://github.com/cert-ee/cuckoo3/issues) and use the "Bug report" template:

### Suggesting Enhancements

We welcome suggestions to improve Cuckoo3. To propose an enhancement:

- Open an [issue](https://github.com/cert-ee/cuckoo3/issues) and use the "Feature request" template.

### Improve documentation

Keeping documentation up to date takes effort. You are welcome to contribute to documentation.

- Open an [issue](https://github.com/cert-ee/cuckoo3/issues) and use the "Documentation" template.

### Contributing Code

- **Discuss First**: It's a good idea to start by opening an issue to discuss your plans.
- **Follow Coding Standards**: Ensure your code adheres to our [Coding Standards](#coding-standards).
- **Update Documentation**: If your changes affect documentation, please update it accordingly.
- **Write Tests**: Include unit tests for new features or bug fixes.
- **Commit Changes**: Make atomic commits with clear messages.
- **Submit a Pull Request**:

  1. Push your branch to your forked repository.

     ```bash
     git push origin feature/your-feature-name
     ```

  2. Open a pull request against the \`main\` branch of the main repository.
  3. Fill out the pull request template, providing all necessary details.

---

## Development Guidelines

### Coding Standards

- **Language**: Python 3.10
- **Style Guide**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style.
- **Documentation**: Use docstrings to document modules, classes, and functions.
- **Dependencies**: Avoid adding unnecessary dependencies.

### Commit Messages

- **Format**: Use the imperative mood in your subject line (e.g., "Add feature" not "Added feature").
- **Subject Line**: Keep it concise (50 characters or less).
- **Body**: If necessary, include a detailed description of the changes.

### Testing

- **Unit Tests**: Write unit tests for all new features and bug fixes.
- **Test Framework**: Use [pytest](https://docs.pytest.org/) for writing tests.
- **Continuous Integration**: Ensure all tests pass before submitting a pull request.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to understand the expectations for all contributors.

---

## License

We are [CLA free](https://ossbase.org/initiatives/cla-free/)

---

## Contact Us

- **Issues**: For bugs or enhancement suggestions, please use the [GitHub Issues](https://github.com/cert-ee/cuckoo3/issues).
- **Email**: For other inquiries, contact the maintainers at [cuckoo@cert.ee](mailto:cuckoo@cert.ee).

---

Thank you for helping to make Cuckoo3 better!
"""
