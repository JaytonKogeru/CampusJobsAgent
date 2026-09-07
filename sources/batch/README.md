# Batch crawl target lists

These YAML files are reusable target waves for large 2027 campus-recruitment sweeps. Copy a file's contents into a GitHub issue whose title starts with `[crawl]` to use the batch mode implemented by `campus_jobs.issue_runner`.

- `2027-expanded-wave1.yaml`: first 20 high-value official/public recruiting targets across consumer electronics, semiconductor and robotics/automotive.

Keep target URLs public and bounded. Failed targets are isolated; successful targets are still committed under the issue run directory.
