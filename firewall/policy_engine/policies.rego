package firewall.policy

import rego.v1

# Default: allow if not blocked
default allow := true

# Block if any blocking condition is met
block if {
    heuristic_blocked
}

block if {
    high_prompt_injection_score
}

block if {
    high_pii_score
}

block if {
    high_toxicity_score
}

block if {
    prompt_too_long
}

# Blocking conditions
heuristic_blocked if {
    input.ml_signals.heuristic_blocked == true
}

high_prompt_injection_score if {
    input.ml_signals.prompt_injection_score > 0.8
}

high_pii_score if {
    input.ml_signals.pii_score > 0.8
}

high_toxicity_score if {
    input.ml_signals.toxicity_score > 0.7
}

prompt_too_long if {
    input.features.length > 4000
}

# Decision output
decision := {
    "blocked": block,
    "reason": reason,
    "matched_rule": matched_rule,
    "confidence": confidence,
} if {
    block
}

decision := {
    "blocked": false,
    "reason": null,
    "matched_rule": null,
    "confidence": 0.5,
} if {
    not block
}

# Determine reason and matched rule (priority order)
reason := "Heuristic detection blocked" if {
    heuristic_blocked
}

reason := "Prompt injection detected" if {
    high_prompt_injection_score
    not heuristic_blocked
}

reason := "High PII score detected" if {
    high_pii_score
    not heuristic_blocked
    not high_prompt_injection_score
}

reason := "High toxicity score detected" if {
    high_toxicity_score
    not heuristic_blocked
    not high_prompt_injection_score
    not high_pii_score
}

reason := "Prompt too long" if {
    prompt_too_long
    not heuristic_blocked
    not high_prompt_injection_score
    not high_pii_score
    not high_toxicity_score
}

matched_rule := "heuristic_block" if {
    heuristic_blocked
}

matched_rule := "prompt_injection_threshold" if {
    high_prompt_injection_score
    not heuristic_blocked
}

matched_rule := "pii_threshold" if {
    high_pii_score
    not heuristic_blocked
    not high_prompt_injection_score
}

matched_rule := "toxicity_threshold" if {
    high_toxicity_score
    not heuristic_blocked
    not high_prompt_injection_score
    not high_pii_score
}

matched_rule := "max_length" if {
    prompt_too_long
    not heuristic_blocked
    not high_prompt_injection_score
    not high_pii_score
    not high_toxicity_score
}

# Confidence based on conditions
confidence := 0.9 if {
    block
}

confidence := 0.5 if {
    not block
}
