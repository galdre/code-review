# Classifying findings

Every proven finding gets one label. The general rule is: **does this PR make something in the product worse than
it was before?** What "worse" means is specific to each PR, so propose criteria and let the user decide.

## Labels

| Label | Meaning |
|---|---|
| **Required** | The PR must not ship (or must be corrected) with this problem. |
| **Requested** | The PR makes something worse, or adds a problem, and the review asks the author to correct it. |
| **Optional** | The problem exists in the same way without this PR. A correction is welcome but not needed here. |

Disproven findings get no label; they go in the report's "Disproven findings" section.

A finding whose correct behavior depends on a design choice (its test has basis "target", or the PR does the thing on
purpose) gets no label and status Decision. Put such findings in one section that states the choice, its costs on
both sides, and any specification rule that bears on it.

Write the label definitions you agree with the user into the report's section 1.3, and use the same words in the
page's `howto`. "Optional" in practice covers both SAME findings and small NEW ones; say so if that is the case.

## Required: decided case by case

Obvious categories, as a starting point:
- the feature does not work as the PR says it does;
- a security problem;
- data loss;
- the change is plainly broken;
- code of unacceptable quality;
- docstrings or comments that are false, and large amounts of prose bloat.

## Requested versus Optional

Use the base-commit check. NEW and WORSE findings are candidates for Requested; SAME findings are candidates for
Optional. Name the specific comparison for this PR. For example, a PR that added a new content type to an existing
sync asked: "does the problem occur only for the new type, or is it worse for the new type than for the types that
already existed?"

## Asking the user

Never ask finding by finding. Present one executive report:
1. The proposed criteria for this PR, in two or three sentences.
2. A table: finding, proposed label, one-line reason, and the evidence class (NEW, WORSE, SAME, BETTER).
3. The borderline cases, each with the full context needed to decide. When a case turns on a standard or on
   client behavior the user may not know, give the rule, its link, and what each kind of client does.

When unsure whether a finding is Required or Requested, put it in the borderline list. The user's labels are
final; record them in the report and do not change them without asking.
