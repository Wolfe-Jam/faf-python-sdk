#!/usr/bin/env python3
"""
Basic FAF SDK usage example

Demonstrates parsing, validation, and data access.
"""

from faf_sdk import parse, validate, find_faf_file

# Example FAF content
EXAMPLE_FAF = """
faf_version: 2.5.0
ai_score: 85%
ai_confidence: HIGH

project:
  name: example-project
  goal: Demonstrate FAF SDK usage
  main_language: Python

instant_context:
  what_building: Example Python application
  tech_stack: Python 3.11, FastAPI, PostgreSQL
  deployment: Docker on AWS
  key_files:
    - src/main.py
    - src/api.py
    - src/models.py
  commands:
    dev: python -m uvicorn main:app --reload
    test: pytest
    build: docker build -t example .

stack:
  frontend: None
  backend: FastAPI
  database: PostgreSQL
  infrastructure: AWS ECS
  testing: pytest
  cicd: GitHub Actions

human_context:
  who: API developers
  what: RESTful API service
  why: Need fast, reliable API endpoints
  how: Domain-driven design
  where: AWS us-east-1
  when: Q1 2025 launch

preferences:
  quality_bar: zero_errors
  testing: required
  documentation: inline

tags:
  - python
  - fastapi
  - api
  - docker
"""


def main():
    # Parse FAF content
    print("Parsing FAF content...")
    faf = parse(EXAMPLE_FAF)

    # Quick access properties
    print(f"\nProject: {faf.project_name}")
    print(f"Score: {faf.score}%")
    print(f"Version: {faf.version}")

    # Typed data access
    print(f"\nGoal: {faf.data.project.goal}")
    print(f"Language: {faf.data.project.main_language}")

    # Instant context
    if faf.data.instant_context:
        ic = faf.data.instant_context
        print(f"\nWhat building: {ic.what_building}")
        print(f"Tech stack: {ic.tech_stack}")
        print(f"Key files: {', '.join(ic.key_files)}")

    # Stack info
    if faf.data.stack:
        stack = faf.data.stack
        print(f"\nStack:")
        print(f"  Backend: {stack.backend}")
        print(f"  Database: {stack.database}")
        print(f"  Testing: {stack.testing}")

    # Human context
    if faf.data.human_context:
        hc = faf.data.human_context
        print(f"\nHuman context:")
        print(f"  Who: {hc.who}")
        print(f"  What: {hc.what}")
        print(f"  Why: {hc.why}")

    # Validation
    print("\n" + "=" * 40)
    print("Validating...")
    result = validate(faf)

    print(f"Valid: {result.valid}")
    print(f"Score: {result.score}%")

    if result.errors:
        print(f"Errors: {result.errors}")

    if result.warnings:
        print(f"Warnings: {result.warnings}")

    # Raw dict access
    print("\n" + "=" * 40)
    print("Raw access:")
    print(f"Tags: {faf.raw.get('tags', [])}")

    print("\nDone!")


if __name__ == "__main__":
    main()
