---
name: repair-unit-tests
description: Schedules one additional test run after a failed verification. Use once when unit tests fail and before publishing a failed result.
---

# Repair unit tests

Schedule the run-unit-tests skill a single time. Do not edit application code to make a failure pass, and do not retry forever. If the second run fails, publish the failure.
