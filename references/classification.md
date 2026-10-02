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
2. A table: finding, proposed label, one-line reason, and the evidence class (NEW, WORSE, SAME).
3. The borderline cases, each with the full context needed to decide.

When unsure whether a finding is Required or Requested, put it in the borderline list. The user's labels are
final; record them in the report and do not change them without asking.
