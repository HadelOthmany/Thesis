from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel
from sympy import And, Implies, Not, Symbol, symbols
from sympy.logic.inference import satisfiable


class Proposition(BaseModel):
    subject: str
    predicate: str
    object: str
    polarity: bool


class RuleCondition(BaseModel):
    subject_var: str
    predicate: str
    object: str
    polarity: bool


class RuleConsequent(BaseModel):
    subject_var: str
    predicate: str
    object: str
    polarity: bool


class Rule(BaseModel):
    type: Literal["implication"] = "implication"
    if_: List[RuleCondition]
    then: RuleConsequent

    class Config:
        populate_by_name = True

    def __init__(self, **data):
        if "if" in data and "if_" not in data:
            data["if_"] = data.pop("if")
        super().__init__(**data)

    def model_dump_alias(self) -> Dict[str, Any]:
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        data["if"] = data.pop("if_")
        return data


class ExtractionResult(BaseModel):
    propositions: List[Proposition]
    rules: List[Rule] = []


def normalize_token(token: str) -> str:
    token = token.strip().rstrip(".")
    return "I" if token.lower() == "i" else token.lower()


def singularize_simple(word: str) -> str:
    w = normalize_token(word)
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"\.\s*", text.strip())
    return [p.strip() for p in parts if p.strip()]


def extract_propositions_and_rules(text: str) -> Dict[str, Any]:
    propositions: List[Dict[str, Any]] = []
    rules: List[Dict[str, Any]] = []

    sentences = split_sentences(text)

    for sentence in sentences:
        s = sentence.strip()

        m = re.match(r"^([A-Z][a-zA-Z]*)\s+is\s+not\s+(?:a\s+|an\s+)?([a-zA-Z]+)$", s)
        if m:
            propositions.append({
                "subject": normalize_token(m.group(1)),
                "predicate": "be",
                "object": singularize_simple(m.group(2)),
                "polarity": False
            })
            continue

        m = re.match(r"^([A-Z][a-zA-Z]*)\s+is\s+(?:a\s+|an\s+)?([a-zA-Z]+)$", s)
        if m:
            propositions.append({
                "subject": normalize_token(m.group(1)),
                "predicate": "be",
                "object": singularize_simple(m.group(2)),
                "polarity": True
            })
            continue

        m = re.match(r"^I\s+do\s+not\s+like\s+([a-zA-Z]+)$", s, re.IGNORECASE)
        if m:
            propositions.append({
                "subject": "I",
                "predicate": "like",
                "object": singularize_simple(m.group(1)),
                "polarity": False
            })
            continue

        m = re.match(r"^I\s+like\s+([a-zA-Z]+)$", s, re.IGNORECASE)
        if m:
            propositions.append({
                "subject": "I",
                "predicate": "like",
                "object": normalize_token(m.group(1)),
                "polarity": True
            })
            continue

        m = re.match(r"^([A-Z][a-zA-Z]*)\s+likes\s+([A-Z]?[a-zA-Z]+)$", s)
        if m:
            propositions.append({
                "subject": normalize_token(m.group(1)),
                "predicate": "like",
                "object": normalize_token(m.group(2)),
                "polarity": True
            })
            continue

        m = re.match(r"^All\s+([a-zA-Z]+)\s+are\s+([a-zA-Z]+)$", s, re.IGNORECASE)
        if m:
            rules.append({
                "type": "implication",
                "if": [
                    {"subject_var": "x", "predicate": "be", "object": singularize_simple(m.group(1)), "polarity": True}
                ],
                "then": {
                    "subject_var": "x",
                    "predicate": "be",
                    "object": singularize_simple(m.group(2)),
                    "polarity": True
                }
            })
            continue

        m = re.match(
            r"^([a-zA-Z]+)\s*,\s*([a-zA-Z]+)\s+things\s+are\s+not\s+([a-zA-Z]+)$",
            s,
            re.IGNORECASE
        )
        if m:
            rules.append({
                "type": "implication",
                "if": [
                    {"subject_var": "x", "predicate": "be", "object": singularize_simple(m.group(1)), "polarity": True},
                    {"subject_var": "x", "predicate": "be", "object": singularize_simple(m.group(2)), "polarity": True}
                ],
                "then": {
                    "subject_var": "x",
                    "predicate": "be",
                    "object": singularize_simple(m.group(3)),
                    "polarity": False
                }
            })
            continue
                # Pattern 8: If someone is (not) X, then they are (not) Y
        m = re.match(
            r"^If someone is\s+(not\s+)?([a-zA-Z]+),\s*then they are\s+(not\s+)?([a-zA-Z]+)$",
            s,
            re.IGNORECASE
        )
        if m:
            antecedent_neg = m.group(1) is not None
            antecedent_obj = singularize_simple(m.group(2))
            consequent_neg = m.group(3) is not None
            consequent_obj = singularize_simple(m.group(4))

            rules.append({
                "type": "implication",
                "if": [
                    {
                        "subject_var": "x",
                        "predicate": "be",
                        "object": antecedent_obj,
                        "polarity": not antecedent_neg
                    }
                ],
                "then": {
                    "subject_var": "x",
                    "predicate": "be",
                    "object": consequent_obj,
                    "polarity": not consequent_neg
                }
            })
            continue

    return {"propositions": propositions, "rules": rules}


def validate_extraction(data: Dict[str, Any]) -> ExtractionResult:
    if hasattr(ExtractionResult, "model_validate"):
        return ExtractionResult.model_validate(data)
    return ExtractionResult.parse_obj(data)


def dump_model(model: BaseModel) -> Dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def prop_key(subject: str, predicate: str, obj: str) -> str:
    return f"{predicate}({subject},{obj})"


def get_symbol(symbol_table: Dict[str, Symbol], key: str) -> Symbol:
    if key not in symbol_table:
        symbol_table[key] = symbols(f"p{len(symbol_table)}")
    return symbol_table[key]


def proposition_to_expr(prop: Proposition, symbol_table: Dict[str, Symbol]):
    sym = get_symbol(symbol_table, prop_key(prop.subject, prop.predicate, prop.object))
    return sym if prop.polarity else Not(sym)


def proposition_to_readable(prop: Proposition) -> str:
    atom = f'{prop.predicate}({prop.subject}, {prop.object})'
    return atom if prop.polarity else f'NOT {atom}'


def collect_entities(result: ExtractionResult) -> Set[str]:
    return {p.subject for p in result.propositions if p.subject != "I"}


def instantiate_condition(condition: RuleCondition, entity: str, symbol_table: Dict[str, Symbol]):
    sym = get_symbol(symbol_table, prop_key(entity, condition.predicate, condition.object))
    return sym if condition.polarity else Not(sym)


def instantiate_consequent(consequent: RuleConsequent, entity: str, symbol_table: Dict[str, Symbol]):
    sym = get_symbol(symbol_table, prop_key(entity, consequent.predicate, consequent.object))
    return sym if consequent.polarity else Not(sym)


def instantiate_rule_readable(rule: Rule, entity: str) -> str:
    left = []
    for c in rule.if_:
        atom = f"{c.predicate}({entity}, {c.object})"
        left.append(atom if c.polarity else f"NOT {atom}")
    then = rule.then
    right_atom = f"{then.predicate}({entity}, {then.object})"
    right = right_atom if then.polarity else f"NOT {right_atom}"
    return f'({" AND ".join(left)}) -> {right}'


def build_formula(result: ExtractionResult) -> Tuple[Any, Dict[str, Symbol], List[str]]:
    symbol_table: Dict[str, Symbol] = {}
    readable_parts: List[str] = []
    expr_parts: List[Any] = []

    for p in result.propositions:
        expr_parts.append(proposition_to_expr(p, symbol_table))
        readable_parts.append(proposition_to_readable(p))

    entities = collect_entities(result)
    for rule in result.rules:
        for entity in sorted(entities):
            lhs_parts = [instantiate_condition(c, entity, symbol_table) for c in rule.if_]
            lhs = And(*lhs_parts) if len(lhs_parts) > 1 else lhs_parts[0]
            rhs = instantiate_consequent(rule.then, entity, symbol_table)
            expr_parts.append(Implies(lhs, rhs))
            readable_parts.append(instantiate_rule_readable(rule, entity))

    full_formula = And(*expr_parts) if expr_parts else None
    return full_formula, symbol_table, readable_parts


def check_satisfiability(formula) -> Tuple[str, Optional[Dict[str, bool]]]:
    result = satisfiable(formula)
    if result is False:
        return "UNSAT", None
    return "SAT", {str(k): bool(v) for k, v in result.items()}


def analyze_text(text: str, output_path: str = "result.json") -> Dict[str, Any]:
    raw = extract_propositions_and_rules(text)
    validated = validate_extraction(raw)

    formula, symbol_table, readable_parts = build_formula(validated)
    sat_label, model = check_satisfiability(formula)

    output: Dict[str, Any] = {
        "input_text": text,
        "validated_json": {
            "propositions": [dump_model(p) for p in validated.propositions],
            "rules": [r.model_dump_alias() for r in validated.rules],
        },
        "formula_parts": readable_parts,
        "full_formula": " AND ".join(readable_parts),
        "sympy_symbol_mapping": {k: str(v) for k, v in symbol_table.items()},
        "satisfiability": sat_label,
        "sat_model": model,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output


def read_text_from_keyboard() -> str:
    print("Paste or type your text. Press Enter on an empty line to finish:\n")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line.strip())
    return " ".join(lines)


if __name__ == "__main__":
    text = read_text_from_keyboard()
    if not text:
        print("No text entered.")
    else:
        result = analyze_text(text, output_path="result.json")

        print("\nValidated JSON:")
        print(json.dumps(result["validated_json"], indent=2, ensure_ascii=False))

        print("\nFormula:")
        print(result["full_formula"])

        print("\nSatisfiability:")
        print(result["satisfiability"])

        print("\nSaved to result.json")
