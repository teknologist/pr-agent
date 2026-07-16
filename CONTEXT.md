# Domain Glossary

## Review

An evaluation of a pull request that produces findings for its authors and reviewers.

## Review strategy

The method used to perform a Review. A Review has exactly one active Review strategy.

## Standard Review

The default Review strategy, in which one reviewer produces the Review.

## Council Review

An optional Review strategy in which multiple Council Members independently evaluate the pull request and a Council Chair produces the collective Review. Council Members may perform Peer Evaluation before synthesis. Selecting Council Review changes how manually and automatically triggered Reviews are performed, not the resulting Review contract, and does not affect answers or introduce a separate user command.

## Council Member

A reviewer that independently evaluates a pull request as one participant in a Council Review. A Council Review has at least two Council Members; members need not use distinct model identities.

## Council Quorum

The minimum participation required to continue a Council Review: at least two Council Members must complete their independent evaluations successfully.

## Peer Evaluation

An optional, advisory Council Review stage in which Council Members assess one another’s proposed findings before synthesis. Peer Evaluation failure does not prevent synthesis once Council Quorum has been reached.

## Council Chair

The reviewer responsible for synthesizing Council Members’ work into the final Council Review.

## Member Fallback

A recovery outcome used when the Council Chair fails: the highest peer-ranked Council Member’s Review becomes the final Review. If no valid ranking exists, no Member Fallback is possible.
