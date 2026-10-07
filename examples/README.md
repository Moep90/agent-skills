# Examples

## demo-project

A tiny, self-contained Kapitan project used in the docs and as the end-to-end test bed. Two
targets (`dev`, `prod`) share a class that renders a greeting per target through a jinja2
component, so it compiles with no external binaries. Its `compiled/` output is committed and
must stay reproducible: the e2e tests assert that a clean compile produces an empty diff.
