# CURRENT_TASK

Ticket: DATA-007
State: READY
Next required actor: Sr Dev - Claude Sonnet 5
Next ticket authorized: NONE

## Summary

DATA-007 is reopened by REVIEW-0233. Five probe implementations bypass their
supplied mock clients and can contact public networks during CI. The correction is
narrow: route supplied mocks through the existing live probe paths without changing
real live behavior or the accepted research artifact.

## Governing documents

- tickets/DATA-007.md
- docs/reviews/REVIEW-0233_DATA-007_REOPENED_CHANGES_REQUIRED.md
