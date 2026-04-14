# Thesis The code used in the Project on LLM Inconsistencies
# Text to Logic Pipeline for SAT/UNSAT Detection

This project implements a simple text-to-logic pipeline that takes natural language input, extracts structured propositions and logical rules, builds a Boolean formula, and checks whether the final result is satisfiable (SAT) or unsatisfiable (UNSAT).

The purpose of this script is to support experiments on detecting logical inconsistencies in text using structured representations and symbolic reasoning.

## What the script does

The script:

- reads text from the keyboard
- extracts propositions and rules from the input text
- validates the extracted structure using Pydantic
- constructs a logical formula using SymPy
- checks satisfiability using symbolic reasoning
- saves the result in a JSON file

## Supported extraction patterns

The current version supports a number of simple natural language patterns, including:

- `Anne is red`
- `Anne is not red`
- `I like dogs`
- `I do not like dogs`
- `Bob likes Alice`
- `All dogs are animals`
- `Big, red things are not quiet`
- `If someone is furry, then they are nice`
- `If someone is not big, then they are quiet`

These patterns are converted into:

- **atomic propositions**
- **implication rules**
- **Boolean logic expressions**

## Project structure

At the moment, the implementation is contained in one script:

- `text_to_logic_pipeline_keyboard.py` — main script for reading input, extracting logic, building formulas, checking satisfiability, and saving results

## Requirements

Install the required Python libraries before running the script:

```bash
pip install pydantic sympy
